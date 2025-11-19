#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vanna 服务测试脚本
用于测试 vanna_service.py 提供的各个 API 接口
"""

import requests
import json
import time
import sys
import io

# 设置stdout为UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:5000"

def print_response(title, response):
    """格式化打印响应"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应: {response.text}")

def test_health():
    """测试健康检查接口"""
    response = requests.get(f"{BASE_URL}/health")
    print_response("1. 健康检查", response)
    return response.status_code == 200

def test_init():
    """测试初始化接口"""
    response = requests.post(f"{BASE_URL}/api/vanna/init")
    print_response("2. 初始化服务", response)
    return response.status_code == 200

def test_train_ddl_preview():
    """测试预览DDL训练"""
    data = {
        "schema": "public"
    }
    response = requests.post(
        f"{BASE_URL}/api/vanna/train/ddl/preview",
        headers={"Content-Type": "application/json"},
        json=data
    )
    print_response("3. 预览DDL训练", response)
    
    # 返回 session_id 用于后续测试
    if response.status_code == 200:
        result = response.json()
        return True, result.get('session_id')
    return False, None

def test_train_documentation_preview():
    """测试预览文档训练"""
    data = {
        "documentation": "PostGIS是PostgreSQL的空间数据库扩展。ST_AsGeoJSON函数将几何体转换为GeoJSON格式。"
    }
    response = requests.post(
        f"{BASE_URL}/api/vanna/train/documentation/preview",
        headers={"Content-Type": "application/json"},
        json=data
    )
    print_response("4. 预览文档训练", response)
    
    if response.status_code == 200:
        result = response.json()
        return True, result.get('session_id')
    return False, None

def test_train_sql_preview():
    """测试预览SQL示例训练"""
    data = {
        "question": "如何查询所有空间表？",
        "sql": "SELECT * FROM geometry_columns;"
    }
    response = requests.post(
        f"{BASE_URL}/api/vanna/train/sql/preview",
        headers={"Content-Type": "application/json"},
        json=data
    )
    print_response("5. 预览SQL示例训练", response)
    
    if response.status_code == 200:
        result = response.json()
        return True, result.get('session_id')
    return False, None

def test_train_confirm(session_id):
    """测试确认训练"""
    if not session_id:
        print("\n⚠️  跳过训练确认测试(无有效session_id)")
        return False
    
    data = {
        "session_id": session_id
    }
    response = requests.post(
        f"{BASE_URL}/api/vanna/train/confirm",
        headers={"Content-Type": "application/json"},
        json=data
    )
    print_response(f"6. 确认训练 (session: {session_id})", response)
    return response.status_code == 200

def test_train_cancel(session_id):
    """测试取消训练"""
    if not session_id:
        print("\n⚠️  跳过取消训练测试(无有效session_id)")
        return False
    
    data = {
        "session_id": session_id
    }
    response = requests.post(
        f"{BASE_URL}/api/vanna/train/cancel",
        headers={"Content-Type": "application/json"},
        json=data
    )
    print_response(f"7. 取消训练 (session: {session_id})", response)
    return response.status_code == 200

def test_generate_sql():
    """测试生成 SQL 接口"""
    data = {
        "question": "查询所有空间表的名称和几何列"
    }
    response = requests.post(
        f"{BASE_URL}/api/vanna/generate_sql",
        headers={"Content-Type": "application/json"},
        json=data
    )
    print_response("8. 生成 SQL", response)
    
    # 返回生成的SQL用于后续测试
    if response.status_code == 200:
        result = response.json()
        return True, result.get('generated_sql')
    return False, None

def test_execute_sql(sql):
    """测试执行 SQL"""
    if not sql:
        print("\n⚠️  跳过SQL执行测试(无有效SQL)")
        return False
    
    data = {
        "sql": sql,
        "confirmed": True
    }
    response = requests.post(
        f"{BASE_URL}/api/vanna/execute_sql",
        headers={"Content-Type": "application/json"},
        json=data
    )
    print_response("9. 执行 SQL", response)
    return response.status_code == 200

def test_get_training_data():
    """测试获取训练数据"""
    response = requests.get(f"{BASE_URL}/api/vanna/training_data")
    print_response("10. 获取训练数据", response)
    
    # 返回第一个训练数据的ID用于测试删除
    if response.status_code == 200:
        result = response.json()
        training_data = result.get('training_data', [])
        if training_data and len(training_data) > 0:
            # 假设训练数据有id字段
            first_id = training_data[0].get('id')
            return True, first_id
    return True, None  # 即使没有数据也算成功

def test_delete_training_data(data_id):
    """测试删除训练数据"""
    if not data_id:
        print("\n⚠️  跳过删除训练数据测试(无有效data_id)")
        return False
    
    response = requests.delete(f"{BASE_URL}/api/vanna/training_data/{data_id}")
    print_response(f"11. 删除训练数据 (id: {data_id})", response)
    return response.status_code == 200

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Vanna 服务测试开始")
    print("="*60)
    print(f"目标服务: {BASE_URL}")
    print("请确保 vanna_service.py 已经启动!")
    print("\n等待 3 秒...")
    time.sleep(3)
    
    results = []
    
    # 1. 健康检查
    try:
        success = test_health()
        results.append(("健康检查", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '健康检查' 失败: {e}")
        results.append(("健康检查", False))
    
    # 2. 初始化服务
    try:
        success = test_init()
        results.append(("初始化服务", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '初始化服务' 失败: {e}")
        results.append(("初始化服务", False))
    
    # 3. 预览DDL训练
    ddl_session_id = None
    try:
        success, ddl_session_id = test_train_ddl_preview()
        results.append(("预览DDL训练", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '预览DDL训练' 失败: {e}")
        results.append(("预览DDL训练", False))
    
    # 4. 预览文档训练
    doc_session_id = None
    try:
        success, doc_session_id = test_train_documentation_preview()
        results.append(("预览文档训练", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '预览文档训练' 失败: {e}")
        results.append(("预览文档训练", False))
    
    # 5. 预览SQL示例训练
    sql_session_id = None
    try:
        success, sql_session_id = test_train_sql_preview()
        results.append(("预览SQL示例训练", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '预览SQL示例训练' 失败: {e}")
        results.append(("预览SQL示例训练", False))
    
    # 6. 确认训练 (使用文档训练的session)
    try:
        success = test_train_confirm(doc_session_id)
        results.append(("确认训练", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '确认训练' 失败: {e}")
        results.append(("确认训练", False))
    
    # 7. 取消训练 (使用DDL训练的session)
    try:
        success = test_train_cancel(ddl_session_id)
        results.append(("取消训练", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '取消训练' 失败: {e}")
        results.append(("取消训练", False))
    
    # 8. 生成SQL
    generated_sql = None
    try:
        success, generated_sql = test_generate_sql()
        results.append(("生成SQL", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '生成SQL' 失败: {e}")
        results.append(("生成SQL", False))
    
    # 9. 执行SQL
    try:
        success = test_execute_sql(generated_sql)
        results.append(("执行SQL", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '执行SQL' 失败: {e}")
        results.append(("执行SQL", False))
    
    # 10. 获取训练数据
    training_data_id = None
    try:
        success, training_data_id = test_get_training_data()
        results.append(("获取训练数据", success))
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 测试 '获取训练数据' 失败: {e}")
        results.append(("获取训练数据", False))
    
    # 11. 删除训练数据 (注意:这会删除真实数据,默认跳过)
    # 如果需要测试删除功能,请取消下面的注释
    # try:
    #     success = test_delete_training_data(training_data_id)
    #     results.append(("删除训练数据", success))
    #     time.sleep(1)
    # except Exception as e:
    #     print(f"\n❌ 测试 '删除训练数据' 失败: {e}")
    #     results.append(("删除训练数据", False))
    
    print("\n⚠️  删除训练数据测试已跳过(防止误删真实数据)")
    results.append(("删除训练数据", None))
    
    # 打印测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    for name, success in results:
        if success is None:
            status = "⊘ 跳过"
        elif success:
            status = "✓ 通过"
        else:
            status = "✗ 失败"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, success in results if success is True)
    total = sum(1 for _, success in results if success is not None)
    print(f"\n总计: {passed}/{total} 测试通过")
    print("="*60)

if __name__ == "__main__":
    main()
