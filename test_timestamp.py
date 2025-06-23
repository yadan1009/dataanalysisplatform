import json
import pandas as pd
import numpy as np
from datetime import datetime

# 创建包含Timestamp类型的DataFrame
df = pd.DataFrame({
    '日期': pd.date_range('2023-01-01', periods=3),
    '数值': [1, 2, 3],
    '名称': ['A', 'B', 'C']
})

print("原始DataFrame:")
print(df)
print("\n数据类型:")
print(df.dtypes)

# 尝试直接转换为JSON (会失败)
print("\n尝试直接转换为JSON:")
try:
    # 转换为字典
    data_dict = df.to_dict(orient='records')
    print("字典内容:", data_dict)
    
    # 尝试JSON序列化
    json_str = json.dumps(data_dict)
    print("JSON转换成功:", json_str)
except Exception as e:
    print("JSON转换失败:", str(e))

# 使用改进的方法处理
print("\n使用改进的处理方法:")
# 创建深拷贝，避免修改原始数据
preview_df = df.copy()

# 处理日期时间类型
for col in preview_df.columns:
    if pd.api.types.is_datetime64_any_dtype(preview_df[col]):
        print(f"转换日期列 {col}")
        preview_df[col] = preview_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    elif preview_df[col].dtype == 'object':
        print(f"处理对象列 {col}")
        preview_df[col] = preview_df[col].astype(str)

# 转换为字典并序列化
data_dict = preview_df.to_dict(orient='records')
print("处理后字典内容:", data_dict)
json_str = json.dumps(data_dict)
print("JSON转换成功:", json_str)

# 测试value_counts的处理
print("\n测试分类列的处理:")
dates = pd.date_range('2023-01-01', periods=5)
test_df = pd.DataFrame({
    '日期类别': [dates[0], dates[1], dates[0], dates[2], dates[0]]
})
print(test_df)

# 获取value_counts
value_counts = test_df['日期类别'].value_counts().to_dict()
print("原始value_counts:", value_counts)

# 处理Timestamp键
formatted_counts = {}
for k, v in value_counts.items():
    # 将键转换为字符串
    if hasattr(k, 'strftime'):  # 如果是日期时间类型
        key = k.strftime('%Y-%m-%d %H:%M:%S')
    else:
        key = str(k)
    formatted_counts[key] = v

print("格式化后value_counts:", formatted_counts)

# 尝试JSON序列化
try:
    json_str = json.dumps(formatted_counts)
    print("JSON转换成功:", json_str)
except Exception as e:
    print("JSON转换失败:", str(e)) 