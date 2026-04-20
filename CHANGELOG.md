# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2024-04-20

### Added
- Windows compatibility using msvcrt for terminal operations
- Debug output for WezTerm/Kitty commands (enabled with TERMA_DEBUG=1)
- Sample images in README.md
- Version constant in terma.py
- CHANGELOG.md file

### Changed
- Updated version to 0.2.1 in pyproject.toml and terma.py
- Refactored terminal handling to support both curses (Unix) and msvcrt (Windows)
- Improved error handling and terminal detection
- Added debug statements throughout the codebase

### Fixed
- Windows terminal compatibility issues
- Missing debug output for command execution
- Terminal size detection on Windows

## [0.2.0] - 2024-04-20

### Added
- Initial Windows support
- Basic debug functionality

## [0.1.2] - 2024-04-10

### Added
- Package installation support with pyproject.toml
- Argument handling improvements
- --help option

### Changed
- Enhanced argument parsing
- Improved error messages

## [0.1.1] - 2024-04-09

### Added
- Package installation support
- pyproject.toml configuration

## [0.1.0] - 2024-04-08

### Added
- Initial implementation of TerMa v0.1.0
- Kitty and WezTerm renderer support
- Basic manga viewing functionality
- Cover and spread page display
- Keyboard navigation (j/k/left/right)
- Mouse support