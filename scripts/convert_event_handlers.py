#!/usr/bin/env python3
"""
自动迁移@event_handler到@workflow.defn的辅助脚本

用法：
    python scripts/convert_event_handlers.py
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple

# 需要处理的文件列表
TARGET_FILES = [
    "app/user/event_handler/handler.py",
    "app/blob/event_handler/handler.py",
    "app/activity_page/event_handler/cross_domain_handler.py",
    "app/activity/event_handler/cross_domain_handler.py",
]


def extract_event_handlers(file_path: Path) -> List[Dict]:
    """提取文件中的所有@event_handler"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配@event_handler装饰器和函数
    pattern = r'@event_handler\((.*?)\)\s*(?:@inject\s*)?(async\s+)?def\s+(\w+)\((.*?)\)\s*->\s*\w+:'
    matches = re.findall(pattern, content, re.DOTALL)
    
    handlers = []
    for match in matches:
        decorator_params = match[0]
        is_async = match[1]
        func_name = match[2]
        func_params = match[3]
        
        # 解析装饰器参数
        event_type = re.search(r'event_type=["\']([^"\']+)', decorator_params)
        handler_id = re.search(r'handler_id=["\']([^"\']+)', decorator_params)
        handler_type = re.search(r'handler_type=["\']([^"\']+)', decorator_params)
        retry = re.search(r'retry=(\d+)', decorator_params)
        
        handlers.append({
            'func_name': func_name,
            'event_type': event_type.group(1) if event_type else '',
            'handler_id': handler_id.group(1) if handler_id else '',
            'handler_type': handler_type.group(1) if handler_type else 'flexible',
            'retry': int(retry.group(1)) if retry else 3,
            'is_async': bool(is_async),
            'params': func_params
        })
    
    return handlers


def generate_workflow_code(handlers: List[Dict], domain: str) -> str:
    """生成Workflow代码"""
    template = f'''"""
{domain.title()} Domain Workflows
自动生成，请根据实际业务调整
"""

from temporalio import workflow, activity
from datetime import timedelta
from pami_event_framework import WorkflowBase

# TODO: 导入必要的依赖
# from dependency_injector.wiring import inject, Provide
# from app.container import Container


# ============ Activities ============

'''
    
    # 生成Activities
    for handler in handlers:
        func_name = handler['func_name']
        activity_name = f"{func_name}_activity"
        
        template += f'''@activity.defn
async def {activity_name}(event_data: dict):
    """TODO: 实现业务逻辑"""
    # 原handler: {func_name}
    # 事件类型: {handler['event_type']}
    pass


'''
    
    template += '\n# ============ Workflows ============\n\n'
    
    # 生成Workflows
    for handler in handlers:
        func_name = handler['func_name']
        # 转换为PascalCase
        workflow_name = ''.join(word.capitalize() for word in func_name.split('_')) + 'Workflow'
        activity_name = f"{func_name}_activity"
        
        retry_attempts = handler['retry']
        
        template += f'''@workflow.defn
class {workflow_name}(WorkflowBase):
    """
    事件: {handler['event_type']}
    Handler ID: {handler['handler_id']}
    类型: {handler['handler_type']}
    """
    
    @workflow.run
    async def run(self, event_data: dict):
        self.log_workflow_start(event_data)
        
        try:
            await workflow.execute_activity(
                {activity_name},
                args=[event_data.get('payload', event_data)],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=workflow.RetryPolicy(maximum_attempts={retry_attempts})
            )
            
            self.log_workflow_complete()
            
        except Exception as e:
            self.log_workflow_error(e)
            raise


'''
    
    return template


def main():
    """主函数"""
    print("="*60)
    print("自动迁移@event_handler到@workflow.defn")
    print("="*60)
    
    root_path = Path('.')
    
    for file_path_str in TARGET_FILES:
        file_path = root_path / file_path_str
        
        if not file_path.exists():
            print(f"[SKIP] 文件不存在: {file_path}")
            continue
        
        print(f"\n处理: {file_path}")
        
        # 提取handlers
        handlers = extract_event_handlers(file_path)
        
        if not handlers:
            print(f"  未找到@event_handler装饰器")
            continue
        
        print(f"  找到 {len(handlers)} 个handler:")
        for h in handlers:
            print(f"    - {h['func_name']} ({h['event_type']})")
        
        # 确定域名
        if 'user' in str(file_path):
            domain = 'user'
        elif 'blob' in str(file_path):
            domain = 'blob'
        elif 'activity_page' in str(file_path):
            domain = 'page'
        elif 'activity' in str(file_path):
            domain = 'activity'
        else:
            domain = 'unknown'
        
        # 生成代码
        workflow_code = generate_workflow_code(handlers, domain)
        
        # 输出文件
        output_file = root_path / 'app' / 'workflows' / f'{domain}_workflows.py'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(workflow_code)
        
        print(f"  [OK] Generated: {output_file}")
    
    print("\n" + "="*60)
    print("Done! Please review and adjust the generated workflow files.")
    print("="*60)


if __name__ == '__main__':
    main()
