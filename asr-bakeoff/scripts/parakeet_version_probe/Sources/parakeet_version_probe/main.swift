import AVFoundation
import CoreML
import FluidAudio
import Foundation

// Parakeet version bake-off probe.
//
// Runs FluidAudio's own BATCH sliding-window `AsrManager.transcribe` over a
// list of wav files for one (version, encoder precision) arm and writes the
// repo's run-dir shape so `scripts/score_corpus_wer.py` and
// `scripts/score_number_fidelity.py --corpus` read it unchanged:
//
//   <out>/per-file/<id>_after_orphan.json  {"segments":[{startTime,endTime,text}]}
//   <out>/manifest.json
//
// Text is written RAW: no inverse text normalization, no filler filtering.
// The scorers own both.
//
// This process is NOT the app. It never touches the `app.mimicscribe`
// UserDefaults domain and never prunes or moves a model file.

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
    let confidence: Double
    let tokenTimings: Int
}

struct Manifest: Codable {
    let arm: String
    let modelVersion: String
    let encoderPrecision: String
    let fluidAudioRevision: String
    let fluidAudioSourcePath: String
    let modelDirectory: String
    let modelFiles: [String: Int]
    let melChunkContextOverride: String
    let seamGapRepair: Bool
    let dualDecodeArbitration: Bool
    let computeUnits: String
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

guard let outPath = argValue("--out"),
    let armName = argValue("--arm"),
    let versionRaw = argValue("--version")
else {
    fputs(
        """
        usage: parakeet_version_probe --arm <name> --version <v2|v3> \\
            [--precision <int8|int8-v2|int4>] --out <dir> \\
            --models-dir <dir> --audio <file1> [--audio <file2> ...]
        """, stderr)
    exit(2)
}

let modelVersion: AsrModelVersion
switch versionRaw.lowercased() {
case "v2", "2": modelVersion = .v2
case "v3", "3": modelVersion = .v3
default:
    fputs("ERROR: unknown --version \(versionRaw)\n", stderr)
    exit(2)
}

let precisionRaw = argValue("--precision") ?? "int8"
guard let precision = ParakeetEncoderPrecision(rawValue: precisionRaw.lowercased()) else {
    fputs("ERROR: unknown --precision \(precisionRaw)\n", stderr)
    exit(2)
}

guard let modelsDir = argValue("--models-dir") else {
    fputs("ERROR: --models-dir is required (the probe must not download into the app's cache)\n", stderr)
    exit(2)
}

// Every `--audio <path>` occurrence, in order.
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

/// Directory size in bytes (a `.mlmodelc` is a directory).
func sizeOnDisk(_ url: URL) -> Int {
    var total = 0
    let fm = FileManager.default
    guard
        let e = fm.enumerator(
            at: url, includingPropertiesForKeys: [.fileSizeKey, .isRegularFileKey])
    else { return 0 }
    for case let f as URL in e {
        let v = try? f.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey])
        if v?.isRegularFile == true { total += v?.fileSize ?? 0 }
    }
    return total
}

func audioDuration(_ url: URL) -> Double {
    guard let f = try? AVAudioFile(forReading: url) else { return 0 }
    return Double(f.length) / f.processingFormat.sampleRate
}

let boundary = "\u{2581}"  // SentencePiece word boundary

/// The span the token timings cover: (first token start, last token end).
func timingSpan(_ timings: [TokenTiming]) -> (Double, Double)? {
    guard let f = timings.first, let l = timings.last else { return nil }
    return (f.startTime, max(l.endTime, f.startTime))
}

/// Rows built from `ASRResult.text`, which is the authoritative output of the
/// batch path.
///
/// WHY NOT REBUILD FROM `tokenTimings`: the two do not agree. `result.text`
/// is decoded from the token IDs through the vocabulary, while `TokenTiming`
/// carries an already-normalized token string, and a numeric piece loses its
/// SentencePiece word boundary on the way (`in 30 minutes` rebuilds as
/// `in30 minutes`). Taking the text verbatim keeps every arm's hypothesis
/// byte-exact; row TIMES are interpolated by word index across the token
/// span, which is enough for the scorers (they sort rows by startTime and
/// concatenate) and is applied identically to every arm.
func rows(text: String, span: (Double, Double)?, duration: Double) -> [Segment] {
    let ws = text.split(whereSeparator: { $0 == " " || $0 == "\n" || $0 == "\t" }).map(String.init)
    guard !ws.isEmpty else { return [] }
    let (t0, t1) = span ?? (0, duration)
    let total = Double(ws.count)
    func time(_ i: Int) -> Double { t0 + (t1 - t0) * (Double(i) / total) }

    var segs: [Segment] = []
    var cur: [String] = []
    var startIdx = 0
    for (i, w) in ws.enumerated() {
        if cur.isEmpty { startIdx = i }
        cur.append(w)
        let terminal = w.hasSuffix(".") || w.hasSuffix("?") || w.hasSuffix("!")
        if (terminal && cur.count >= 3) || cur.count >= 60 {
            segs.append(
                Segment(
                    startTime: time(startIdx), endTime: time(i + 1),
                    text: cur.joined(separator: " ")))
            cur = []
        }
    }
    if !cur.isEmpty {
        segs.append(
            Segment(
                startTime: time(startIdx), endTime: time(ws.count),
                text: cur.joined(separator: " ")))
    }
    return segs
}

func collapse(_ s: String) -> String {
    s.split(whereSeparator: { $0 == " " || $0 == "\n" || $0 == "\t" }).joined(separator: " ")
}

func iso(_ d: Date) -> String {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime]
    return f.string(from: d)
}

// MARK: - load

let modelsParent = URL(fileURLWithPath: modelsDir, isDirectory: true)
// `AsrModelVersion.repo` is internal; the repo folder name is recovered from
// the public default cache path so the probe cannot mis-name a directory.
let repoFolder = AsrModels.defaultCacheDirectory(for: modelVersion).lastPathComponent
let targetDir = modelsParent.appendingPathComponent(repoFolder, isDirectory: true)

FileManager.default.changeCurrentDirectoryPath(FileManager.default.currentDirectoryPath)

fputs("[probe] arm=\(armName) version=\(versionRaw) precision=\(precision.rawValue)\n", stderr)
fputs("[probe] models under \(targetDir.path)\n", stderr)

// `download` never uses force, so it can only ADD missing files.
let resolvedDir = try await AsrModels.download(
    to: targetDir, force: false, version: modelVersion, encoderPrecision: precision)
let models = try await AsrModels.load(
    from: resolvedDir, version: modelVersion, encoderPrecision: precision)

var modelFiles: [String: Int] = [:]
if let entries = try? FileManager.default.contentsOfDirectory(
    at: resolvedDir, includingPropertiesForKeys: nil)
{
    for e in entries {
        modelFiles[e.lastPathComponent] = sizeOnDisk(e)
    }
}

let asrConfig = ASRConfig(
    tdtConfig: TdtConfig(blankId: modelVersion.blankId),
    encoderHiddenSize: modelVersion.encoderHiddenSize
)
let manager = AsrManager(config: asrConfig)
try await manager.loadModels(models)
let decoderLayers = await manager.decoderLayerCount

let startedAt = Date()
var stats: [FileStat] = []

for path in audioFiles {
    let url = URL(fileURLWithPath: path)
    let id = url.deletingPathExtension().lastPathComponent
    let dur = audioDuration(url)

    // A fresh decoder state per file: each file is an independent decode, the
    // same way the corpus pipeline treats them.
    var state = TdtDecoderState.make(decoderLayers: decoderLayers)
    let t0 = Date()
    let result = try await manager.transcribe(url, decoderState: &state, language: nil)
    let wall = Date().timeIntervalSince(t0)

    let timings = result.tokenTimings ?? []
    let segs = rows(text: collapse(result.text), span: timingSpan(timings), duration: dur)

    let enc = JSONEncoder()
    enc.outputFormatting = [.prettyPrinted, .sortedKeys]
    let data = try enc.encode(PerFile(segments: segs))
    try data.write(
        to: perFileDir.appendingPathComponent("\(id)_after_orphan.json"), options: .atomic)

    let wordCount = collapse(result.text).split(separator: " ").count
    stats.append(
        FileStat(
            id: id, audioSeconds: dur, wallSeconds: wall,
            realtimeFactor: wall > 0 ? dur / wall : 0,
            words: wordCount, segments: segs.count,
            confidence: Double(result.confidence), tokenTimings: timings.count))
    fputs(
        String(
            format: "[probe] %@  %.1fs audio  %.1fs wall  RTFx %.1f  %d words  %d rows\n",
            id, dur, wall, wall > 0 ? dur / wall : 0, wordCount, segs.count), stderr)
}

let finishedAt = Date()
let totalAudio = stats.reduce(0.0) { $0 + $1.audioSeconds }
let totalWall = stats.reduce(0.0) { $0 + $1.wallSeconds }

let manifest = Manifest(
    arm: armName,
    modelVersion: versionRaw,
    encoderPrecision: modelVersion == .v3 ? precision.rawValue : "n/a (v2 ships one encoder)",
    fluidAudioRevision: "3c2cd9c22f0118eccdcf3bf9ae7bea3ea12fc9a0",
    fluidAudioSourcePath: "resolved by SwiftPM from Package.swift (MimicScribe/FluidAudio at the pinned revision)",
    modelDirectory: resolvedDir.path,
    modelFiles: modelFiles,
    melChunkContextOverride: "nil (library default: false on v3, true on v2)",
    seamGapRepair: asrConfig.seamGapRepair,
    dualDecodeArbitration: asrConfig.dualDecodeArbitration,
    computeUnits: "cpuAndNeuralEngine (preprocessor cpuOnly) — FluidAudio default",
    decodePath: "AsrManager.transcribe(URL) batch sliding window (disk-backed above 30s)",
    segmentTimeBasis: "row TEXT verbatim from ASRResult.text; row TIMES interpolated by "
        + "word index across the token-timing span (identical treatment for every arm)",
    startedAt: iso(startedAt),
    finishedAt: iso(finishedAt),
    totalAudioSeconds: totalAudio,
    totalWallSeconds: totalWall,
    aggregateRealtimeFactor: totalWall > 0 ? totalAudio / totalWall : 0,
    files: stats
)
let menc = JSONEncoder()
menc.outputFormatting = [.prettyPrinted, .sortedKeys]
try menc.encode(manifest).write(to: out.appendingPathComponent("manifest.json"), options: .atomic)

fputs(
    String(
        format: "[probe] DONE %@  %.0fs audio  %.0fs wall  aggregate RTFx %.1f\n",
        armName, totalAudio, totalWall, totalWall > 0 ? totalAudio / totalWall : 0), stderr)
