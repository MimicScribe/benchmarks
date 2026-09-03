// swift-tools-version: 6.0
import PackageDescription

// Standalone probe package. It depends on the SAME FluidAudio revision the app
// pins — the fork URL and sha copied verbatim from the root `Package.swift`
// (`MimicScribe/FluidAudio` @ 3c2cd9c22f0118eccdcf3bf9ae7bea3ea12fc9a0, =
// branch sas-support-rebased-2026-08-20: upstream v0.15.6 + the SAS patches +
// the three #523 reverts; inventory in docs/FLUIDAUDIO_FORK.md) — so the
// comparison cannot drift from production's library and the package resolves
// on any machine with network access, not only inside this checkout.
//
// If the app re-pins FluidAudio, re-pin this sha in the same commit or the
// probe stops measuring production's library.
//
// Nothing here is part of the app build.
let package = Package(
    name: "parakeet-version-probe",
    platforms: [.macOS("15.0")],
    dependencies: [
        .package(
            url: "https://github.com/MimicScribe/FluidAudio.git",
            revision: "3c2cd9c22f0118eccdcf3bf9ae7bea3ea12fc9a0")
    ],
    targets: [
        .executableTarget(
            name: "parakeet_version_probe",
            dependencies: [.product(name: "FluidAudio", package: "FluidAudio")],
            path: "Sources/parakeet_version_probe"
        )
    ]
)
