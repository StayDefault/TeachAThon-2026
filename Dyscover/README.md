# DysCover · 前端

最新原型功能、开发进度和完整使用指南见 [Dyscover Prototype Overview](../PROTOTYPE_OVERVIEW.md)（英文）。该文档区分真实 AI 模式与脚本演示模式，并记录当前限制。

给有阅读障碍的大学生用的**全语音学习工具**。把课件、作业说明、笔记照片拖到白板上，语音助教会一边和你聊，一边长出一张思维导图；你理解错的地方会用橙色标出来并讲清楚。

> 给 coding agent：请先读 **[AGENTS.md](AGENTS.md)**（英文，含架构、接口、产品规则）。接口细节见 **[docs/API.md](docs/API.md)**。

## 一分钟跑起来

```bash
npm install
npm run dev
```

打开 http://localhost:5173 ，点 **Use demo files → Start studying**，就能看到完整演示：

1. 文件卡片飞进中间的学习盒
2. 盒子飞到右上角，语音问你了解多少
3. 导图一个节点一个节点长出来，实时字幕同步
4. 你"说错"一句话后，对应节点变成橙色"已纠正"
5. 点任意节点：右侧浮窗显示原文出处（高亮）、概念解释和编辑选项；点击节点不会自动播放语音
6. 左上角 Past sessions 打开历史记录侧边栏
7. 底部玻璃对话栏：语音一直开着，点一下结束 / 恢复；点左边键盘切到文字模式
8. 顶部 Conversation 单独查看整个学习会话的对话记录；真实模式下，创建或编辑节点会自动得到 AI 审阅反馈

默认开发模式使用**假后端**（`src/api/mock.ts`），对话是预设脚本，不需要服务器。真实后端也已实现；设置 `VITE_USE_MOCK=false` 并启动 Python 服务后，可使用实际上传、AI 对话、自动节点审阅和 SQLite 保存。

## 前后端分工

| 前端（已完成） | 后端（本地原型已实现） |
|---|---|
| 全部界面、动画、状态管理 | 解析上传文件（按页提取文字，图片 OCR） |
| 麦克风采集、语音播放、音量驱动小球 | 语音流程：语音识别 → 大模型 → 语音合成 |
| 收到事件就更新导图 / 字幕 | 校验大模型的结构化 JSON 方案，更新导图、纠错或提出删除建议 |
| 历史会话列表、节点详情面板 | 保存会话、导图、对话记录；回答节点详情 |

接口约定全部写在 `docs/API.md`，前端的真实请求代码在 `src/api/http.ts`。本地后端的安装与运行步骤见 [`../backend/README.md`](../backend/README.md)。设置 `OPENAI_API_KEY` 并在 `.env` 里设 `VITE_USE_MOCK=false`，即可使用真实文件和本地后端。

## 目录

```
src/types.ts          数据结构（前后端共用的约定）
src/api/              mock.ts 假后端 · http.ts 真后端客户端
src/state/store.tsx   全局状态，处理后端推送的事件
src/screens/          首页、学习页
src/components/       导图、节点面板、对话栏、字幕、侧边栏……
docs/API.md           接口文档
AGENTS.md             给 AI 编程助手看的说明
```

## 技术栈

React 18 + TypeScript + Vite，无 UI 库，纯 CSS。字体 Lexend（专为易读性设计）。

## 截图

`docs/screenshots/` 里有每个主要页面的截图，可以先看效果再跑代码。
