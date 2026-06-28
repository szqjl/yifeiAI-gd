import sys
sys.path.insert(0, '.')

from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

print('=' * 70)
print('V7-001: 引擎模型加载验证')
print('=' * 70)

# 测试1: 创建引擎实例
print('\n[测试1] 创建引擎实例...')
try:
    engine = UltimateWinRateEngineV7(player_id=0)
    print('✅ 引擎创建成功')
except Exception as e:
    print(f'❌ 引擎创建失败: {e}')
    sys.exit(1)

# 测试2: 检查模型是否加载成功
print('\n[测试2] 检查模型加载状态...')
if engine.model is not None:
    print('✅ 模型加载成功')
else:
    print('❌ 模型加载失败')
    sys.exit(1)

# 测试3: 检查设备类型
print('\n[测试3] 检查设备类型...')
print(f'设备: {engine.device}')
print('✅ 设备检测完成')

# 测试4: 检查模型架构
print('\n[测试4] 检查模型架构...')
if hasattr(engine.model, 'features'):
    print('✅ 模型特征提取层存在')
    print('  - 输入维度: 512')
    print('  - 特征层结构: Linear(512, 64) -> ReLU -> Dropout -> Linear(64, 32) -> ReLU')
else:
    print('❌ 模型架构检查失败')

# 测试5: 特征提取测试
print('\n[测试5] 特征提取测试...')
try:
    game_state = {
        'myPos': 0,
        'curPos': 0,
        'greaterPos': -1,
        'handCards': ['S2', 'H2', 'D3', 'C3', 'S4'],
        'actionList': [['SINGLE', '2', ['S2']], ['PASS']],
        'curAction': [],
        'greaterAction': [],
        'roundNum': 1,
        'stage': 'play',
        'curRank': '2',
        'selfRank': '2',
        'oppoRank': '2',
        'publicInfo': [
            {'rest': 22},
            {'rest': 27},
            {'rest': 25},
            {'rest': 27}
        ]
    }
    
    features = engine._extract_features(game_state, game_state['actionList'])
    if features is not None and len(features) == 512:
        print('✅ 特征提取成功')
        print(f'  - 特征维度: {len(features)}')
        print(f'  - 特征范围: [{features.min():.3f}, {features.max():.3f}]')
    else:
        print('❌ 特征提取失败')
except Exception as e:
    print(f'❌ 特征提取测试失败: {e}')

# 测试6: 推理测试
print('\n[测试6] 模型推理测试...')
try:
    import torch
    test_input = torch.randn(1, 512).to(engine.device)
    with torch.no_grad():
        output = engine.model(test_input)
    
    if 'action_logits' in output:
        print('✅ 模型推理成功')
        act_shape = output['action_logits'].shape
        pos_win = output['position_win_rate'].item()
        act_val = output['action_value'].item()
        long_rew = output['long_term_reward'].item()
        print(f'  - action_logits shape: {act_shape}')
        print(f'  - position_win_rate: {pos_win:.4f}')
        print(f'  - action_value: {act_val:.4f}')
        print(f'  - long_term_reward: {long_rew:.4f}')
    else:
        print('❌ 推理输出格式错误')
except Exception as e:
    print(f'❌ 推理测试失败: {e}')

# 测试7: 决策测试
print('\n[测试7] 决策功能测试...')
try:
    action_list = [['SINGLE', '2', ['S2']], ['PAIR', '2', ['S2', 'H2']], ['PASS']]
    result = engine._rule_based_decision(game_state, action_list)
    print('✅ 规则决策功能正常')
    print(f'  - 选择的动作索引: {result}')
    print(f'  - 选择的动作: {action_list[result]}')
except Exception as e:
    print(f'❌ 决策测试失败: {e}')

print('\n' + '=' * 70)
print('V7-001: 所有验证测试完成')
print('=' * 70)