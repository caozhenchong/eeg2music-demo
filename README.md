# EEG2Music Demo

独立运行的脑电音乐演示工程。项目包含 EEG 文件读取、信号预处理、特征分析、V-A 语义映射、GUI 可视化、MIDI 生成和 JSON 结果保存，不引用其他业务工程的模块或路径。

## 快速运行

```powershell
cd "F:\研究项目\MER\eeg2music_demo_app"
py -m pip install -r requirements.txt
py main.py
```

无界面自检：

```powershell
py main.py --self-test --seconds 10
```

## 分层结构

```text
eeg2music_demo_app/
├── main.py                         # 程序入口
├── requirements.txt               # 独立依赖
└── eeg2music/
    ├── bootstrap.py                # 依赖装配（Composition Root）
    ├── config.py                   # 配置和常量
    ├── domain/                     # 领域实体与接口
    │   ├── models.py
    │   └── ports.py
    ├── application/                # 应用用例/业务编排
    │   └── eeg2music_service.py
    ├── infrastructure/             # 技术实现
    │   ├── eeg/                    # MNE 读取与 SciPy EEG 分析
    │   ├── semantics/              # 演示 V-A 与音乐映射
    │   └── output/                 # MIDI、JSON 本地输出
    └── ui/                         # Tkinter 展示层
        ├── main_window.py
        └── charts.py
```

依赖方向为：

```text
GUI -> Application -> Domain Ports <- Infrastructure
                       ^
                       └── bootstrap 负责注入具体实现
```

GUI 只调用应用服务；应用服务只依赖领域接口；MNE、SciPy、文件输出等实现通过 `bootstrap.py` 注入。因此数据源、分析模型或输出方式都可以独立替换。

## 本地算法流程

1. MNE 读取 CNT/EDF/BDF/FIF，统一转换为微伏；
2. 非有限值修复、鲁棒去尖峰；
3. 50 Hz 陷波、0.5–45 Hz 带通；
4. 坏导检测和 CAR 共平均重参考；
5. Welch PSD、五频带绝对/相对功率、个体 Alpha 峰；
6. 信号质量评分；
7. 演示 V-A 解码和音乐控制映射；
8. 生成 MIDI 与 JSON。

## 正式算法替换点

搜索“此处可接入实际算法”即可定位：

- `HeuristicBrainStateDecoder`：替换为训练后的连续 V-A 推理服务；
- `RuleBasedMusicMapper`：替换为 Brain-Music Semantic Bridge；
- `midi_writer.py`：替换为 Music Transformer 输出。

当前 V-A 和旋律规则只用于界面与流程演示，不用于临床或科学结论。
