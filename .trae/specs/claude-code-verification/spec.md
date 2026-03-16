# Claude Code 验证与模型配置 Spec

## Why
用户需要验证 Claude Code 是否正确安装，并了解系统中 Claude Code 的调用模型配置，以便正确使用 Claude AI 进行开发工作。

## What Changes
- 检查 Claude Code CLI 是否已安装
- 验证 Claude Code 安装完整性
- 查看 Claude Code 的默认调用模型
- 如未安装，提供安装指导

## Impact
- Affected specs: AI 模型配置
- Affected code: 无代码变更，仅验证和配置检查

## ADDED Requirements

### Requirement: Claude Code Installation Verification
The system SHALL verify Claude Code CLI installation status.

#### Scenario: Claude Code is installed
- **WHEN** user runs `claude --version`
- **THEN** system displays Claude Code version information

#### Scenario: Claude Code is not installed
- **WHEN** user runs `claude --version`
- **THEN** system displays "command not found" or similar error
- **AND** user is provided with installation instructions

### Requirement: Claude Code Model Configuration
The system SHALL display Claude Code's default model configuration.

#### Scenario: View default model
- **WHEN** user requests Claude Code model information
- **THEN** system displays the default model name (e.g., claude-sonnet-4-20250514)
- **AND** system displays available model options

### Requirement: Claude Code Functionality Test
The system SHALL verify Claude Code can communicate with Anthropic API.

#### Scenario: API connection test
- **WHEN** user runs a simple Claude Code command
- **THEN** Claude Code successfully connects to Anthropic API
- **AND** returns a valid response
