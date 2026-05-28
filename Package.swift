// swift-tools-version:5.9
// This package exists only to generate DocC documentation for the SpecGraph
// Python project. The runtime implementation lives under tools/.

import PackageDescription

let package = Package(
    name: "SpecGraph",
    products: [
        .library(
            name: "SpecGraph",
            targets: ["SpecGraph"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-docc-plugin", from: "1.0.0"),
    ],
    targets: [
        .target(
            name: "SpecGraph",
            path: "Sources/SpecGraph",
            exclude: []
        ),
    ]
)
