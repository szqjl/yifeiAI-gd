"""
诊断模块测试

测试配置文件检测、输出捕获、游戏次数提取和诊断报告生成功能。
"""

import os
import sys
import subprocess
import tempfile
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from batch_executor.diagnostic import DiagnosticModule, DiagnosticReport


class TestConfigFileDetection:
    """测试配置文件检测功能"""
    
    @given(
        config_files=st.lists(
            st.sampled_from([
                'config.ini', 'config.json', 'config.yaml', 'config.yml',
                'settings.txt', 'settings.ini', 'settings.json',
                'configuration.ini', 'configuration.json',
                '.config', 'app.config'
            ]),
            min_size=0,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_config_file_detection_completeness(self, config_files):
        """
        **Feature: batch-game-execution, Property 1: 配置文件检测完整性**
        **Validates: Requirements 0.1**
        
        For any 服务器目录，如果目录中存在配置文件，系统应该能够检测到所有这些文件
        """
        # 为每次测试创建新的临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置文件
            for config_file in config_files:
                file_path = os.path.join(temp_dir, config_file)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('test content')
            
            # 执行检测
            diagnostic = DiagnosticModule()
            found_files = diagnostic.check_config_files(temp_dir)
            
            # 验证：所有创建的配置文件都应该被检测到
            assert set(found_files) == set(config_files), \
                f"Expected to find {config_files}, but found {found_files}"
            
            # 验证：返回的列表应该是排序的
            assert found_files == sorted(found_files), \
                "Found files should be sorted"


class TestOutputCapture:
    """测试输出捕获功能"""
    
    @given(
        output_lines=st.lists(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=('Lu', 'Ll', 'Nd'),
                    whitelist_characters=' :.-_'
                ),
                min_size=1,
                max_size=50
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_output_capture_completeness(self, output_lines):
        """
        **Feature: batch-game-execution, Property 2: 输出捕获完整性**
        **Validates: Requirements 0.3**
        
        For any 服务器进程输出，系统应该能够捕获并记录所有输出内容
        """
        # 过滤掉空行和只有空格的行
        output_lines = [line.strip() for line in output_lines if line.strip()]
        
        if not output_lines:
            return  # 跳过空输出的情况
        
        # 创建一个简单的脚本来输出这些行
        script_content = "import sys\n"
        for line in output_lines:
            # 转义单引号
            escaped_line = line.replace("'", "\\'")
            script_content += f"print('{escaped_line}')\n"
        
        # 写入临时脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # 启动进程
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 捕获输出
            diagnostic = DiagnosticModule()
            captured = diagnostic.capture_server_output(process, timeout=5)
            
            # 等待进程结束
            process.wait(timeout=5)
            
            # 验证：所有输出行都应该被捕获
            captured_lines = [line.strip() for line in captured.split('\n') if line.strip()]
            
            assert captured_lines == output_lines, \
                f"Expected {output_lines}, but captured {captured_lines}"
        
        finally:
            # 清理临时文件
            if os.path.exists(script_path):
                os.remove(script_path)


class TestGameCountExtraction:
    """测试游戏次数提取功能"""
    
    @given(
        game_count=st.integers(min_value=1, max_value=10000),
        format_choice=st.sampled_from([
            "Game count: {}",
            "游戏次数: {}",
            "游戏场数: {}",
            "Total games: {}",
            "Games: {}",
            "Count: {}",
            "场数: {}",
        ]),
        prefix=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            max_size=20
        ),
        suffix=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            max_size=20
        )
    )
    @settings(max_examples=100)
    def test_property_game_count_extraction_accuracy(self, game_count, format_choice, prefix, suffix):
        """
        **Feature: batch-game-execution, Property 3: 游戏次数提取准确性**
        **Validates: Requirements 0.4**
        
        For any 包含游戏次数信息的服务器输出，系统应该能够正确提取数值
        """
        # 构建包含游戏次数的输出
        game_count_line = format_choice.format(game_count)
        output = f"{prefix}\n{game_count_line}\n{suffix}"
        
        # 提取游戏次数
        diagnostic = DiagnosticModule()
        extracted = diagnostic.extract_game_count(output)
        
        # 验证：提取的数值应该等于原始数值
        assert extracted == game_count, \
            f"Expected to extract {game_count} from '{output}', but got {extracted}"


class TestMismatchDetection:
    """测试参数不匹配检测功能"""
    
    @given(
        expected=st.integers(min_value=1, max_value=1000),
        actual=st.one_of(
            st.none(),
            st.integers(min_value=1, max_value=1000)
        ),
        config_files=st.lists(
            st.sampled_from(['config.ini', 'config.json', 'settings.txt']),
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_mismatch_detection(self, expected, actual, config_files):
        """
        **Feature: batch-game-execution, Property 4: 参数不匹配检测**
        **Validates: Requirements 0.5**
        
        For any 命令行参数和实际游戏次数的组合，当两者不相等时，系统应该能够检测到差异
        """
        diagnostic = DiagnosticModule()
        
        # 构建服务器输出
        server_output = f"Game count: {actual}" if actual else "No game count"
        
        # 执行诊断
        report = diagnostic.diagnose(
            expected=expected,
            actual=actual,
            config_files=config_files,
            server_output=server_output
        )
        
        # 验证：当actual为None或与expected不同时，应该检测到不匹配
        expected_mismatch = (actual is None) or (actual != expected)
        
        assert report.mismatch_detected == expected_mismatch, \
            f"For expected={expected}, actual={actual}: " \
            f"expected mismatch_detected={expected_mismatch}, but got {report.mismatch_detected}"
        
        # 验证报告的基本字段
        assert report.expected_count == expected
        assert report.actual_count == actual
        assert report.config_files_found == config_files
        
        # 验证：如果检测到不匹配，应该有原因和建议
        if report.mismatch_detected:
            assert len(report.possible_causes) > 0, \
                "Should have possible causes when mismatch detected"
            assert len(report.recommendations) > 0, \
                "Should have recommendations when mismatch detected"
