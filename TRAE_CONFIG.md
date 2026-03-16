# Trae IDE 配置指南

## 减少红色代码标注的配置

### 1. 已创建的本地配置文件

已创建 `.trae/settings.json`，包含以下配置：

```json
{
  "python.analysis.typeCheckingMode": "off",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportGeneralTypeIssues": "none",
    "reportMissingImports": "none",
    "reportMissingModuleSource": "none",
    "reportOptionalSubscript": "none",
    "reportOptionalMemberAccess": "none",
    "reportOptionalCall": "none",
    "reportOptionalIterable": "none",
    "reportOptionalContextManager": "none",
    "reportOptionalOperand": "none",
    "reportPrivateImportUsage": "none"
  },
  "python.linting.flake8Enabled": false,
  "python.linting.pylintEnabled": false,
  "python.linting.mypyEnabled": false
}
```

### 2. 手动配置步骤（如本地配置不生效）

在 Trae IDE 中：

1. 打开设置：`File` → `Preferences` → `Settings` (或按 `Ctrl+,`)

2. 搜索 `python.analysis.typeCheckingMode`，设置为 `off`

3. 搜索 `python.analysis.diagnosticSeverityOverrides`，添加以下配置：
   - `reportMissingImports`: `none`
   - `reportMissingModuleSource`: `none`
   - `reportGeneralTypeIssues`: `none`

4. 搜索 `python.linting.enabled`，设置为 `false`（或单独禁用各 linter）

5. 重启 Trae IDE

### 3. 代码风格配置

当前项目使用以下代码风格：

| 配置项 | 值 |
|--------|-----|
| 行宽 | 120 |
| 格式化工具 | black |
| 导入排序 | isort |
| 类型检查 | 关闭 |

### 4. 保留的错误提示

以下问题仍会显示红色标注（建议修复）：
- 未定义变量 (`reportUndefinedVariable`)
- 无效字符串转义 (`reportInvalidStringEscapeSequence`)
- 未绑定变量 (`reportUnboundVariable`)

### 5. 常见问题

**Q: 为什么还有红色标注？**
A: 请检查：
1. 虚拟环境是否正确激活
2. Python 解释器路径是否正确设置
3. 是否安装了必要的依赖包

**Q: 如何完全禁用所有诊断？**
A: 在设置中搜索 `python.analysis.diagnosticMode`，设置为 `off`

**Q: 如何恢复类型检查？**
A: 将 `python.analysis.typeCheckingMode` 改回 `basic` 或 `strict`
