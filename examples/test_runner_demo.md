# 🧪 Test Runner Examples

## Basic Usage

### Run All Tests
```bash
./test
```

### Run Tests with Python
```bash
python3 run_tests.py
```

## Features Demonstrated

### ✅ Success Scenario
When all tests pass, you'll see:
- Green checkmarks (✅) for all tests
- Beautiful progress bars
- Success summary panel
- Tree view of test hierarchy

### ❌ Failure Scenario 
When tests fail, you'll see:
- Red X marks (❌) for failed tests
- Orange explosion marks (💥) for errors
- Detailed failure information
- Full traceback in failure details section

### 📊 Coverage Analysis
If `coverage.py` is installed, the runner will automatically:
- Run coverage analysis on all test files
- Display coverage percentage in summary
- Color-code coverage (green ≥80%, orange ≥60%, red <60%)

## Test Runner Features

### 🎨 Visual Elements
- **Kartoza Color Scheme**: Consistent branding colors
- **Rich Progress Bars**: Real-time test execution progress
- **Status Icons**: ✅ ❌ 💥 ⏭️ for different test outcomes
- **Tree View**: Hierarchical display of modules and tests
- **Panels**: Bordered sections for clear organization

### 📈 Progress Tracking
- **Module Level**: Shows current test module being executed
- **Test Level**: Individual test progress within modules
- **Timing**: Execution time for each test and module
- **Counters**: Running totals of passed/failed/error/skipped tests

### 🔍 Detailed Reporting
- **Summary Table**: Overview of all test metrics
- **Module Breakdown**: Per-module test results and timing
- **Failure Analysis**: Full tracebacks for failed tests
- **Coverage Integration**: Code coverage statistics (if available)

## Exit Codes

- **0**: All tests passed successfully
- **1**: One or more tests failed or errored
- **130**: Test run interrupted by user (Ctrl+C)

## Adding New Tests

Create test files following the pattern `test_*.py` with standard unittest format:

```python
#!/usr/bin/env python3
import unittest

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
```

The test runner will automatically discover and run your tests!