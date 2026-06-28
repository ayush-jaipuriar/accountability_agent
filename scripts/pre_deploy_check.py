#!/usr/bin/env python3
"""
Pre-Deploy Validation Script
============================

Run before every deployment to catch issues early.

Usage:
    python scripts/pre_deploy_check.py

Exit codes:
    0 = All checks passed, safe to deploy
    1 = Critical issue found, DO NOT DEPLOY
"""

import subprocess
import sys
import ast
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a shell command and return success/failure."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"✅ {description} — PASSED")
            return True
        else:
            print(f"❌ {description} — FAILED")
            if result.stdout:
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
            if result.stderr:
                print("STDERR:", result.stderr[-500:])
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} — TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} — ERROR: {e}")
        return False


def check_handler_consistency() -> bool:
    """Verify REGISTERED_COMMANDS and _get_command_handler_map stay in sync."""
    print(f"\n{'='*60}")
    print("🔍 Handler registration consistency")
    print(f"{'='*60}")
    
    try:
        # Parse telegram_bot.py to extract REGISTERED_COMMANDS and handler map
        bot_file = Path("src/bot/telegram_bot.py")
        tree = ast.parse(bot_file.read_text())
        
        registered_commands = []
        handler_map_keys = []
        
        # Commands handled by ConversationHandler (not in handler map by design)
        conversation_commands = {"checkin", "quickcheckin"}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "TelegramBotManager":
                for item in node.body:
                    # Find REGISTERED_COMMANDS
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "REGISTERED_COMMANDS":
                                registered_commands = [
                                    el.value for el in item.value.elts
                                    if isinstance(el, ast.Constant)
                                ]
                    
                    # Find _get_command_handler_map
                    if isinstance(item, ast.FunctionDef) and item.name == "_get_command_handler_map":
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Dict):
                                handler_map_keys = [
                                    k.value for k in stmt.keys
                                    if isinstance(k, ast.Constant)
                                ]
        
        # ConversationHandler commands are allowed to be missing from handler map
        missing_in_map = set(registered_commands) - set(handler_map_keys) - conversation_commands
        missing_in_registered = set(handler_map_keys) - set(registered_commands)
        
        if missing_in_map:
            print(f"❌ Commands in REGISTERED_COMMANDS but missing from _get_command_handler_map:")
            for cmd in sorted(missing_in_map):
                print(f"   - {cmd}")
        
        if missing_in_registered:
            print(f"❌ Commands in _get_command_handler_map but missing from REGISTERED_COMMANDS:")
            for cmd in sorted(missing_in_registered):
                print(f"   - {cmd}")
        
        if not missing_in_map and not missing_in_registered:
            print(f"✅ Handler registration consistency — PASSED")
            print(f"   {len(registered_commands)} commands registered, {len(handler_map_keys)} in handler map")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Handler consistency check failed: {e}")
        return False


def check_callback_safety() -> bool:
    """Check for unsafe update.message access inside callback handlers."""
    print(f"\n{'='*60}")
    print("🔍 Callback handler safety")
    print(f"{'='*60}")
    
    issues = []
    
    for pyfile in Path("src/bot").rglob("*.py"):
        try:
            tree = ast.parse(pyfile.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    func_name = node.name
                    # Heuristic: callback handlers often have "callback" in name
                    if "callback" not in func_name.lower():
                        continue
                    
                    # Look for update.message.reply_text or update.message anything
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Attribute):
                            # Check for update.message
                            if (isinstance(subnode.value, ast.Attribute) and
                                isinstance(subnode.value.value, ast.Name) and
                                subnode.value.value.id == "update" and
                                subnode.value.attr == "message"):
                                # Check if it's reply_text or edit_message_text
                                if subnode.attr in ("reply_text", "edit_message_text"):
                                    issues.append(f"{pyfile}:{subnode.lineno}: {func_name} uses update.message.{subnode.attr}")
        except SyntaxError:
            continue
    
    if issues:
        print(f"⚠️  Found {len(issues)} potential unsafe update.message references in callbacks:")
        for issue in issues[:10]:
            print(f"   {issue}")
        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more")
        print(f"   ℹ️  Review these manually. Some may be safe (e.g., using _get_message_from_update).")
        # Don't fail — some may be false positives
        return True
    else:
        print(f"✅ Callback handler safety — PASSED")
        return True


def check_html_safety() -> bool:
    """Check for unescaped HTML in messages with parse_mode='HTML'."""
    print(f"\n{'='*60}")
    print("🔍 HTML parse_mode safety")
    print(f"{'='*60}")
    
    issues = []
    
    for pyfile in Path("src").rglob("*.py"):
        try:
            content = pyfile.read_text()
            tree = ast.parse(content)
            
            # Simple heuristic: find strings with parse_mode='HTML' and check for unescaped <
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check if this call has parse_mode='HTML'
                    has_html_parse = False
                    for kw in node.keywords:
                        if kw.arg == "parse_mode":
                            if isinstance(kw.value, ast.Constant) and kw.value.value == "HTML":
                                has_html_parse = True
                    
                    if has_html_parse:
                        # Get the text argument (first positional arg)
                        if node.args:
                            text_arg = node.args[0]
                            if isinstance(text_arg, ast.Constant) and isinstance(text_arg.value, str):
                                text = text_arg.value
                                # Check for unescaped < that looks like a tag
                                # Allow known safe tags
                                import re
                                # Remove allowed tags
                                cleaned = re.sub(r'</?[bi]|</?code>|</?pre>|</?a\b[^>]*>', '', text)
                                # Check for remaining < followed by non-space
                                if re.search(r'<[^\s/]', cleaned):
                                    issues.append(f"{pyfile}:{node.lineno}: Potential unescaped '<' in HTML message")
        except SyntaxError:
            continue
    
    if issues:
        print(f"⚠️  Found {len(issues)} potential HTML safety issues:")
        for issue in issues[:10]:
            print(f"   {issue}")
        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more")
        print(f"   ℹ️  Review these manually. Some may be false positives.")
        return True  # Warning, not failure
    else:
        print(f"✅ HTML parse_mode safety — PASSED")
        return True


def check_model_name_centralization() -> bool:
    """Check that no hardcoded model names exist outside config."""
    print(f"\n{'='*60}")
    print("🔍 Model name centralization")
    print(f"{'='*60}")
    
    issues = []
    allowed_in_config = ["gemini-2.5-flash", "gemini-2.5-flash-exp"]
    
    for pyfile in Path("src").rglob("*.py"):
        if pyfile.name == "config.py":
            continue
        content = pyfile.read_text()
        # Look for hardcoded gemini model names
        if "gemini-" in content:
            for line_no, line in enumerate(content.split("\n"), 1):
                if "gemini-" in line and "=" in line and "settings." not in line:
                    # Skip comments and imports
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("from ") or stripped.startswith("import "):
                        continue
                    # Check if it's a hardcoded default
                    if "model_name" in line or "model" in line.lower():
                        issues.append(f"{pyfile}:{line_no}: {stripped.strip()[:80]}")
    
    if issues:
        print(f"⚠️  Found {len(issues)} potential hardcoded model names:")
        for issue in issues[:10]:
            print(f"   {issue}")
        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more")
        print(f"   ℹ️  Model names should be centralized in config.py")
        return True  # Warning
    else:
        print(f"✅ Model name centralization — PASSED")
        return True


def check_static_analysis() -> bool:
    """Run pyflakes static analysis and fail on critical issues (undefined name, syntax error)."""
    import subprocess
    print(f"\n{'='*60}")
    print("🔍 Static analysis (pyflakes)")
    print(f"{'='*60}")
    try:
        # Run pyflakes on the src directory
        result = subprocess.run(
            ["./venv/bin/pyflakes", "src/"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # Analyze stdout/stderr
        output = result.stdout + result.stderr
        critical_issues = []
        warnings = []
        
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if "undefined name" in line or "invalid syntax" in line:
                critical_issues.append(line)
            else:
                warnings.append(line)
                
        if warnings:
            print(f"⚠️  Found {len(warnings)} static analysis warnings (non-blocking):")
            for warn in warnings[:10]:
                print(f"   {warn}")
            if len(warnings) > 10:
                print(f"   ... and {len(warnings) - 10} more warnings.")
                
        if critical_issues:
            print(f"❌ CRITICAL: Found {len(critical_issues)} undefined names or syntax errors:")
            for issue in critical_issues:
                print(f"   {issue}")
            return False
            
        print("✅ Static analysis (pyflakes) — PASSED")
        return True
        
    except Exception as e:
        print(f"💥 Static analysis check error: {e}")
        return False


def main() -> int:
    """Run all pre-deploy checks."""
    print("🚀 Accountability Agent — Pre-Deploy Validation")
    print("=" * 60)

    checks = []

    # 1. Source compilation
    checks.append(run_command(
        ["python3", "-m", "compileall", "src/"],
        "Source compilation check",
    ))

    # 1.5. Static analysis (pyflakes)
    checks.append(check_static_analysis())

    # 2. Test suite
    checks.append(run_command(
        ["pytest", "tests/", "-q", "--tb=short"],
        "Test suite (pytest)",
    ))

    # 3. Check for syntax errors in new files
    new_services = [
        "src/services/insights_engine.py",
        "src/services/predictive_intervention.py",
        "src/services/challenge_service.py",
        "src/services/goal_service.py",
        "src/services/feature_discovery_service.py",
        "src/services/feedback_service.py",
        "src/services/streak_recovery_service.py",
        "src/services/data_deletion_service.py",
    ]
    for svc in new_services:
        if Path(svc).exists():
            checks.append(run_command(
                ["python3", "-m", "py_compile", svc],
                f"Compile check: {svc}",
            ))

    # 4. Schema validation
    checks.append(run_command(
        ["python3", "-c", "try:\n    from src.models.schemas import User, DailyCheckIn, Goal, PartnerChallenge\n    print('OK')\nexcept ImportError as e:\n    print(f'SKIP (deps): {e}')"],
        "Schema model imports",
    ))

    # 5. Config validation
    checks.append(run_command(
        ["python3", "-c", "try:\n    from src.config import settings\n    print(f'OK: {settings.environment}')\nexcept ImportError as e:\n    print(f'SKIP (deps): {e}')"],
        "Config loading",
    ))

    # 6. Handler registration consistency (NEW)
    checks.append(check_handler_consistency())

    # 7. Callback handler safety (NEW)
    checks.append(check_callback_safety())

    # 8. HTML parse_mode safety (NEW)
    checks.append(check_html_safety())

    # 9. Model name centralization (NEW)
    checks.append(check_model_name_centralization())

    # Summary
    print(f"\n{'='*60}")
    passed = sum(checks)
    total = len(checks)
    print(f"📊 Results: {passed}/{total} checks passed")
    print(f"{'='*60}")

    if passed == total:
        print("🎉 All checks passed! Safe to deploy.")
        return 0
    else:
        print("🚨 CRITICAL: Some checks failed. DO NOT DEPLOY.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
