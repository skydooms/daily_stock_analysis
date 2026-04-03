import celpy

# 1. 读取 .cel 文件内容
with open('/media/sky/Data/stock/list/短期买点.sel', 'r') as f:
    cel_source = f.read()

# 2. 创建 CEL 环境
env = celpy.Environment()

# 3. 编译表达式
ast = env.compile(cel_source)
# 4. 创建可执行程序
prgm = env.program(ast)
# 5. 准备执行时需要的变量数据
activation = {
    "account": celpy.json_to_cel({"balance": 1000}),
    "transaction": celpy.json_to_cel({"amount": 500})
}

# 6. 执行表达式并获取结果
result = prgm.evaluate(activation)
print(result)  # 输出: BoolType(True)