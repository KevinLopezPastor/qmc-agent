"""Test script for analyst module"""
import sys
import json
sys.path.insert(0, '.')

# Load actual data
with open('qmc_tasks_20260127_123124.json', 'r') as f:
    data = json.load(f)

from src.analyst import analyst_node_sync

# Simulate state like notebook does
state = {'raw_table_data': json.dumps({'rows': data['tasks']})}

result = analyst_node_sync(state)
for log in result.get('logs', []):
    print(log)
print(f"\nProcess Status Estado: {result.get('process_status', {}).get('estado', 'N/A')}")
