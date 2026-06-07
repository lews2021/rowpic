# rowpic

> **RAW + 标准格式 照片浏览器 / 分析器 / 调色器**
> 支持三分 / 黄金 / 对角等多种构图参考线、人脸虚焦检测、一键归类、AI 调色。
> 可作为**桌面应用** 启动，也可作为**Web 服务器** 部署。

![python](https://img.shields.io/badge/python-3.12-blue) ![backend](https://img.shields.io/badge/FastAPI-0.115-009688) ![frontend](https://img.shields.io/badge/React-18-61dafb) ![tauri](https://img.shields.io/badge/Tauri-2-ffc131)

---

## 1. 主要功能

| 模块 | 说明 |
|---|---|
| 文件夹扫描 | 递归扫描，自动识别 JPEG / PNG / TIFF / WebP / BMP / HEIC **以及全部主流 RAW 格式**(ARW / NEF / CR2/CR3 / RAF / ORF / RW2 / DNG / PEF / SRW / 3FR / IIQ …) |
| 预览大图 | 高质量 JPEG 预览(按需缓存)，支持滚轮缩放、拖拽 |
| 拍摄信息 | 光圈、快门、ISO、镜头、相机、焦距(含35mm等效)、白平衡、闪光灯、拍摄时间、EXIF 原始字段 |
| 直方图 | RGB + 亮度四通道叠加显示；高光/暗部剪切提示 |
| 对焦分析 | Laplacian 方差评估整图锐度 + 局部热力图 |
| 人脸识别 | OpenCV Haar 检测，**逐张评估面部锐度**，标记"脸糊" |
| 构图参考线 | 三分法 / 黄金分割 / 黄金螺旋 / 对角 / 中心十字 / 三角 / 和声 — **鼠标拖拽、滚轮缩放、平移、旋转** |
| 一键归类 | 按 *人脸虚焦 / 全图虚焦 / 欠曝 / 过曝* 自动分类；可移动到子目录 |
| 调色 | 曝光/对比/饱和/振动/色温/色调/高光/阴影/白点/黑点；一键 Auto Tone |
| AI 调色 | 一键 AI Look（默认无依赖的自适应算法）；支持"**从参考图学 Look → 批量应用**"的传输学习式调色，**可零成本挂入 ONNX 模型**（如 Zero-DCE++） |
| 重复检测 | DCT pHash 找出近似重复照片 |

## 2. 项目结构

```
rowpic/
├── backend/                # Python FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由 (photos / color / classify / info / tools)
│   │   ├── core/            # 配置、日志
│   │   ├── models/          # Pydantic schema
│   │   ├── services/        # decoder / exif / focus / color / classifier / scanner / phash
│   │   └── main.py          # 入口
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # React + Vite + TS 前端
│   ├── src/
│   │   ├── api/             # API 客户端 + 类型
│   │   ├── components/      # 组件（核心交互：构图叠加 / 调色 / 对焦 / 直方图 / EXIF）
│   │   ├── styles/global.css
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── desktop/                # Tauri 2 桌面壳（可选）
│   └── src-tauri/
├── scripts/                # 启动 / 测试脚本
│   ├── start_web.py         # Web 模式（开发用，热重载）
│   ├── start_desktop.py     # 桌面模式（pywebview 启动原生窗口）
│   ├── start_server.py      # 服务器模式（生产用）
│   ├── e2e_test.py          # 端到端 API 测试（13 项）
│   ├── make_synthetic_raw.py# 合成 RAW-like 样本（16-bit TIFF）
│   └── *_bat / *_sh         # Windows / Linux 启动脚本
├── samples/                # 演示照片
├── models/                 # 放 ONNX 模型（可选，启用 AI 调色时用）
├── logs/                   # 启动日志
├── Dockerfile              # 多阶段构建（前端 + 后端）
├── docker-compose.yml
└── README.md
```

## 3. 快速开始

### 3.1 准备环境

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.12 | 后端 |
| Node.js | 20+ | 前端开发 |
| (可选) Rust + WebView2 | latest | Tauri 桌面构建 |

```powershell
# 后端依赖
cd backend
python -m pip install -r requirements.txt

# 前端依赖
cd ..\frontend
npm install
```

### 3.2 启动

#### 方式 A — Web 模式（开发用，热重载）
```powershell
python scripts\start_web.py
```
打开 `http://127.0.0.1:5173` ，后端在 `127.0.0.1:8765`。

#### 方式 B — 桌面模式（pywebview 原生窗口）
```powershell
python -m pip install pywebview
python scripts\start_desktop.py
```
打开一个无边框原生窗口（Edge WebView2 / WebKit）。

#### 方式 C — 服务器模式（部署到远程）
```powershell
# 构建前端
cd frontend
npm run build
cd ..

# 启动后端（已挂载前端 dist 到 /ui）
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8765
```
访问 `http://<host>:8765/docs` 查看 OpenAPI 文档，或 `http://<host>:8765/ui` 访问前端 UI。

或者用 Docker：
```powershell
docker compose up -d --build
```

#### 方式 D — Tauri 桌面应用（需 Rust，约 10MB 安装包）
```powershell
# 前置：安装 Rust (https://rustup.rs) + WebView2 (Win10+ 默认有)
rustup default stable
cd desktop\src-tauri
cargo install tauri-cli --version "^2.0"
cargo tauri dev     # 开发模式
cargo tauri build   # 打包为 .msi / .exe
```
Tauri 启动时**自动拉起 Python 后端子进程**，关闭窗口时自动 kill。

### 3.3 端到端验证

```powershell
# 先启动后端（任一方式）
# 然后跑测试
python scripts\e2e_test.py
```
测试覆盖 13 项 API：health / info / scan / thumb / preview / detail / 自动调色 /
手动调色 / AI Look / Learn-Look + Apply-Look / 一键归类 / pHash 重复检测 / 模型信息。

## 4. 使用指南

1. 启动后，在顶栏输入照片目录路径，点 **Scan Folder**（如 `C:\Users\you\Pictures\2025Hokkaido`）。
2. 左侧缩略图列表，点任意照片进入主预览。
3. **EXIF 面板**：相机、镜头、曝光三段信息。
4. **Histogram 面板**：实时 RGB + 亮度直方图。
5. **Focus 面板**：整图锐度评分、每个检测到的人脸的局部锐度、热力图。
6. **主预览右上角**：切换构图参考线（三分 / 黄金 / 螺旋 / 对角 / 中心 / 三角 / 和声）。
   - **拖拽**移动参考线
   - **Shift + 拖拽**整体缩放
   - **滚轮**缩放
   - 重置按钮恢复
7. **Color 面板**：
   - 调整各项参数，预览实时刷新
   - **Auto Tone**：直方图自动拉伸
   - **AI Look ✨**：调起 AI 调色（无模型时走内置算法）
   - **Learn Look**：从当前照片学一个"Look"，然后批量应用到其他照片
8. 顶栏 **One-Click Classify**：按虚焦/对焦/脸糊批量归类，分类结果显示在侧边栏筛选。
9. 顶栏菜单的 **Tools / Duplicates**：用 pHash 找出近似重复照片。

## 5. API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET  | `/api/info` | 服务信息 / 支持格式 |
| GET  | `/healthz` | 健康检查 |
| POST | `/api/photos/scan` | 扫描目录 |
| GET  | `/api/photos/detail` | 详情（EXIF + 直方图 + 对焦） |
| GET  | `/api/photos/thumb` | 缩略图 JPEG |
| GET  | `/api/photos/preview` | 预览图 JPEG |
| GET  | `/api/photos/raw` | 完整像素（编码为 JPEG） |
| POST | `/api/color/adjust_path` | 调色（带 AI 钩子） |
| POST | `/api/color/adjust` | 调色（接收 base64） |
| POST | `/api/color/learn_look` | 从参考图学"AI Look" |
| POST | `/api/color/apply_look` | 把学到的 Look 应用到目标图 |
| GET  | `/api/color/models` | 可用 AI 模型清单 |
| POST | `/api/classify/run` | 批量归类 |
| POST | `/api/tools/duplicates` | pHash 找重复 |
| POST | `/api/tools/phash` | 计算单张 pHash |

完整 OpenAPI 文档：`http://127.0.0.1:8765/docs`

## 6. 配置 (`backend/.env`)
```ini
ROWPIC_HOST=127.0.0.1
ROWPIC_PORT=8765

# 锐度阈值（越小越严格）
ROWPIC_BLUR_THRESHOLD=60
ROWPIC_FACE_BLUR_THRESHOLD=35

# 启用 AI 调色（需先放好 ONNX 模型到 models/）
ROWPIC_ENABLE_AI_COLOR=false
ROWPIC_AI_COLOR_MODEL=auto

# 限制可扫描路径（JSON 列表，留空 = 允许全部；服务器模式推荐配置）
ROWPIC_ALLOWED_ROOTS=["/photos"]
```

## 7. 扩展 AI 调色

`backend/app/services/color_service.py` 内置三档 AI 调色路径：

1. **零成本**（默认）：灰世界白平衡 + 自动曝光 + 直方图匹配 + 振动
2. **Learn & Apply**：从一张参考图提取"look"（通道 CDF + 亮度），批量应用到任意图
3. **ONNX 模型**（可选）：把 `<name>.onnx` 放到 `models/`，调用 `ai_model=<name>`

接 ONNX 模型示例：
```python
# 在 color_service.py 中
import onnxruntime as ort
_sess = ort.InferenceSession("models/zero_dce.onnx", providers=["CPUExecutionProvider"])

def _zero_dce(img):
    x = np.transpose(img, (2,0,1))[None].astype(np.float32)
    y = _sess.run(None, {_sess.get_inputs()[0].name: x})[0]
    return np.clip(np.transpose(y[0], (1,2,0)), 0, 1)

register_ai_model("zero_dce", _zero_dce)
```
模型契约：输入 (1, 3, H, W) float32 [0,1]，输出同形。H、W 需为 8 的倍数。

## 8. 路线图

- [x] RAW 解码 / EXIF / 直方图 / 对焦 / 人脸 / 调色 / AI 钩子
- [x] 构图参考线 + 拖拽 / 缩放
- [x] Tauri 桌面壳
- [x] 一键归类
- [x] pHash 重复检测
- [x] Learn-Look → Apply-Look 调色
- [x] ONNX 模型接入位
- [ ] Lightroom-like 星标 / 标签
- [ ] GPU 加速的 Real-ESRGAN 超分
- [ ] 多语言 i18n
- [ ] 视频缩略图

## 9. 许可

MIT