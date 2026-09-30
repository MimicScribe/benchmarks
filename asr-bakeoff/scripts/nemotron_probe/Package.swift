// swift-tools-version: 6.0
import PackageDescription

// Standalone probe package for the Nemotron Speech Streaming arm. It pins
// UPSTREAM FluidAudio v0.17.4 (FluidInference/FluidAudio, tag v0.17.4), not the
// fork the app and `parakeet_version_probe` pin: the fork is v0.15.6-based and
// has no Nemotron streaming manager. The two packages are kept apart so each
// arm is decoded by exactly the library revision its Provenance row names.
//
// Nothing here is part of the app build.
let package = Package(
    name: "nemotron-probe",
    platforms: [.macOS("15.0")],
    dependencies: [
        .package(
            url: "https://github.com/FluidInference/FluidAudio.git",
            revision: "21493f8dac5a97e65742e6ff26f42f164c2fda0f")
    ],
    targets: [
        .executableTarget(
            name: "nemotron_probe",
            dependencies: [.product(name: "FluidAudio", package: "FluidAudio")],
            path: "Sources/nemotron_probe"
        )
    ]
)
