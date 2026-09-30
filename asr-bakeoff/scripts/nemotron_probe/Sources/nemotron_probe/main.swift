import AVFoundation
import CoreML
import FluidAudio
import Foundation

// Nemotron Speech Streaming 0.6B bake-off probe.
//
// Streams each wav file through FluidAudio's `StreamingNemotronAsrManager`
// exactly as a live caller would — append audio, process what the buffer
// allows, `finish()` at the end — and writes the same run-dir shape as
// `unified_probe`, so `scripts/score_corpus_wer.py`,
// `scripts/score_number_fidelity.py --corpus` and the `scripts/bakeoff/`
// scorers read it unchanged:
//
//   <out>/per-file/<id>_after_orphan.json  {"segments":[{startTime,endTime,text}]}
//   <out>/manifest.json
//
// Text is written RAW: no inverse text normalization, no filler filtering.
// The scorers own both. No vocabulary boosting.
//
// Models are loaded from `--models-dir` with `loadModels(from:)`, which never
// downloads. `--models-dir` is the tier directory itself (the one holding
// `encoder/encoder_int8.mlmodelc`, `decoder_joint.mlmodelc`, `metadata.json`).

struct Segment: Codable {
  let startTime: Double
  let endTime: Double
  let text: String
}

struct PerFile: Codable {
  let segments: [Segment]
}

struct FileStat: Codable {
  let id: String
  let audioSeconds: Double
  let wallSeconds: Double
  let realtimeFactor: Double
  let words: Int
  let segments: Int
  let tokenTimings: Int
  /// The timing-derived text equals `finish()`'s transcript (whitespace
  /// collapsed). Rows are built from the timings, so a false here means the
  /// rows are not the model's transcript.
  let timingsMatchTranscript: Bool
}

struct Manifest: Codable {
  let arm: String
  let model: String
  let tier: String
  let chunkMs: Int
  let chunkSamples: Int
  let feedSeconds: Double
  let fluidAudioRevision: String
  let modelDirectory: String
  let decodePath: String
  let segmentTimeBasis: String
  let startedAt: String
  let finishedAt: String
  let totalAudioSeconds: Double
  let totalWallSeconds: Double
  let aggregateRealtimeFactor: Double
  let files: [FileStat]
}

// MARK: - args

func argValue(_ name: String) -> String? {
  let a = CommandLine.arguments
  guard let i = a.firstIndex(of: name), i + 1 < a.count else { return nil }
  return a[i + 1]
}

guard let outPath = argValue("--out"), let armName = argValue("--arm"),
  let modelsDir = argValue("--models-dir")
else {
  fputs(
    """
    usage: nemotron_probe --arm <name> --out <dir> --models-dir <tier dir> \\
        [--feed-seconds 0.16] --audio <file1> [--audio <file2> ...]
    """, stderr)
  exit(2)
}

// Audio handed to the manager per append. The manager decodes whole chunks
// (2,240 ms on the default tier), so this only has to be no larger than a live
// capture callback.
let feedSeconds = Double(argValue("--feed-seconds") ?? "0.16") ?? 0.16

var audioFiles: [String] = []
do {
  let a = CommandLine.arguments
  var i = 0
  while i < a.count {
    if a[i] == "--audio", i + 1 < a.count {
      audioFiles.append(a[i + 1])
      i += 1
    }
    i += 1
  }
}
guard !audioFiles.isEmpty else {
  fputs("ERROR: no --audio files given\n", stderr)
  exit(2)
}

let out = URL(fileURLWithPath: outPath)
let perFileDir = out.appendingPathComponent("per-file")
try FileManager.default.createDirectory(at: perFileDir, withIntermediateDirectories: true)

// MARK: - helpers

func collapse(_ s: String) -> String {
  s.split(whereSeparator: { $0 == " " || $0 == "\n" || $0 == "\t" }).joined(separator: " ")
}

func iso(_ d: Date) -> String {
  let f = ISO8601DateFormatter()
  f.formatOptions = [.withInternetDateTime]
  return f.string(from: d)
}

/// Words from token timings. The manager builds its transcript by decoding the
/// token ids (`▁` becomes a space), so a token with a leading space starts a new
/// word; each word spans its first token's start to its last token's end.
func words(from timings: [TokenTiming]) -> [(text: String, start: Double, end: Double)] {
  var out: [(text: String, start: Double, end: Double)] = []
  var boundaryPending = true
  for t in timings {
    // rawToken(for:) returns the SentencePiece piece, so `▁` marks a word start.
    let tok = t.token.replacingOccurrences(of: "\u{2581}", with: " ")
    let startsWord = tok.hasPrefix(" ") || boundaryPending
    let piece = tok.trimmingCharacters(in: .whitespaces)
    if piece.isEmpty {
      boundaryPending = boundaryPending || tok.contains(" ")
      continue
    }
    boundaryPending = tok.hasSuffix(" ")
    if startsWord || out.isEmpty {
      out.append((piece, t.startTime, t.endTime))
    } else {
      let last = out[out.count - 1]
      out[out.count - 1] = (last.text + piece, last.start, max(last.end, t.endTime))
    }
  }
  return out
}

/// Rows broken at a sentence terminal (after 3+ words) or at 60 words, the same
/// rule `unified_probe` and `parakeet_version_probe` use, with real word times.
func rows(_ ws: [(text: String, start: Double, end: Double)]) -> [Segment] {
  var segs: [Segment] = []
  var cur: [(text: String, start: Double, end: Double)] = []
  func flush() {
    guard let f = cur.first, let l = cur.last else { return }
    segs.append(
      Segment(
        startTime: f.start, endTime: max(l.end, f.start),
        text: cur.map(\.text).joined(separator: " ")))
    cur = []
  }
  for w in ws {
    cur.append(w)
    let terminal = w.text.hasSuffix(".") || w.text.hasSuffix("?") || w.text.hasSuffix("!")
    if (terminal && cur.count >= 3) || cur.count >= 60 { flush() }
  }
  flush()
  return segs
}

// MARK: - load

let modelDir = URL(fileURLWithPath: modelsDir, isDirectory: true)
guard
  FileManager.default.fileExists(
    atPath: modelDir.appendingPathComponent("encoder/encoder_int8.mlmodelc").path)
else {
  fputs("ERROR: encoder/encoder_int8.mlmodelc not found under \(modelDir.path)\n", stderr)
  exit(2)
}

let manager = StreamingNemotronAsrManager()
try await manager.loadModels(from: modelDir)
let chunkMs = await manager.config.chunkMs
let chunkSamples = await manager.config.chunkSamples
fputs("[nemotron] arm=\(armName) chunk=\(chunkMs)ms models=\(modelDir.path)\n", stderr)

let startedAt = Date()
var stats: [FileStat] = []

// Resume: a file whose output and manifest entry both exist from an earlier
// invocation into the same --out is kept, not re-decoded.
let manifestURL = out.appendingPathComponent("manifest.json")
let previous =
  (try? JSONDecoder().decode(Manifest.self, from: Data(contentsOf: manifestURL)))?.files ?? []

/// One independent streaming decode of `url` from a fresh stream.
func decode(_ url: URL) async throws -> (
  transcript: String, timings: [TokenTiming], wall: Double, dur: Double
) {
  let file = try AVAudioFile(forReading: url)
  let format = file.processingFormat
  let dur = Double(file.length) / format.sampleRate
  let frameCount = AVAudioFrameCount(max(1, Int(feedSeconds * format.sampleRate)))
  await manager.reset()
  let t0 = Date()
  while file.framePosition < file.length {
    guard let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount) else {
      throw ASRError.processingFailed("buffer alloc failed")
    }
    try file.read(into: buf, frameCount: frameCount)
    if buf.frameLength == 0 { break }
    try await manager.appendAudio(buf)
    try await manager.processBufferedAudio()
  }
  let r = try await manager.finishWithTokenTimings()
  return (r.text, r.timings, Date().timeIntervalSince(t0), dur)
}

/// Written after every file, so a crash keeps the files already decoded.
@MainActor func writeManifest() throws {
  let finishedAt = Date()
  let totalAudio = stats.reduce(0.0) { $0 + $1.audioSeconds }
  let totalWall = stats.reduce(0.0) { $0 + $1.wallSeconds }

  let manifest = Manifest(
    arm: armName,
    model: "nvidia/nemotron-speech-streaming-en-0.6b (FluidInference CoreML, int8 encoder)",
    tier: "\(chunkMs)ms",
    chunkMs: chunkMs,
    chunkSamples: chunkSamples,
    feedSeconds: feedSeconds,
    fluidAudioRevision: "21493f8dac5a97e65742e6ff26f42f164c2fda0f (upstream v0.17.4)",
    modelDirectory: modelDir.path,
    decodePath:
      "StreamingNemotronAsrManager: appendAudio + processBufferedAudio per feed, finishWithTokenTimings() at EOF",
    segmentTimeBasis:
      "rows built from finishWithTokenTimings(); word = tokens up to the next leading-space token; "
      + "row = first word start to last word end",
    startedAt: iso(startedAt),
    finishedAt: iso(finishedAt),
    totalAudioSeconds: totalAudio,
    totalWallSeconds: totalWall,
    aggregateRealtimeFactor: totalWall > 0 ? totalAudio / totalWall : 0,
    files: stats
  )
  let menc = JSONEncoder()
  menc.outputFormatting = [.prettyPrinted, .sortedKeys]
  try menc.encode(manifest).write(to: manifestURL, options: .atomic)
}

for path in audioFiles {
  let url = URL(fileURLWithPath: path)
  let id = url.deletingPathExtension().lastPathComponent
  let outFile = perFileDir.appendingPathComponent("\(id)_after_orphan.json")
  if FileManager.default.fileExists(atPath: outFile.path),
    let done = previous.first(where: { $0.id == id })
  {
    stats.append(done)
    fputs("[nemotron] \(id) already decoded, kept\n", stderr)
    continue
  }

  // A CoreML prediction can time out under Neural Engine contention and abort
  // the stream mid-file, so the whole file is re-decoded from a fresh stream.
  var result: (transcript: String, timings: [TokenTiming], wall: Double, dur: Double)?
  for attempt in 1...3 {
    do {
      result = try await decode(url)
      break
    } catch {
      fputs("[nemotron] \(id) attempt \(attempt) failed: \(error.localizedDescription)\n", stderr)
    }
  }
  guard let (transcript, timings, wall, dur) = result else {
    fputs("ERROR \(id): failed 3 times\n", stderr)
    exit(1)
  }

  let ws = words(from: timings)
  let segs = rows(ws)
  let matches = collapse(ws.map(\.text).joined(separator: " ")) == collapse(transcript)
  guard matches else {
    fputs("ERROR \(id): token-timing text differs from finish() transcript\n", stderr)
    exit(1)
  }

  let enc = JSONEncoder()
  enc.outputFormatting = [.prettyPrinted, .sortedKeys]
  try enc.encode(PerFile(segments: segs)).write(to: outFile, options: .atomic)

  stats.append(
    FileStat(
      id: id, audioSeconds: dur, wallSeconds: wall,
      realtimeFactor: wall > 0 ? dur / wall : 0,
      words: ws.count, segments: segs.count, tokenTimings: timings.count,
      timingsMatchTranscript: matches))
  fputs(
    String(
      format: "[nemotron] %@  %.1fs audio  %.1fs wall  RTFx %.1f  %d words  %d rows\n",
      id, dur, wall, wall > 0 ? dur / wall : 0, ws.count, segs.count), stderr)
  try writeManifest()
}

try writeManifest()
let totalAudio = stats.reduce(0.0) { $0 + $1.audioSeconds }
let totalWall = stats.reduce(0.0) { $0 + $1.wallSeconds }

fputs(
  String(
    format: "[nemotron] DONE %@  %.0fs audio  %.0fs wall  aggregate RTFx %.1f\n",
    armName, totalAudio, totalWall, totalWall > 0 ? totalAudio / totalWall : 0), stderr)
