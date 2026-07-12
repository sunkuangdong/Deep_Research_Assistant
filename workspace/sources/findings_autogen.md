# Findings: AutoGen 框架

## 调研范围
本文件覆盖 AutoGen 框架的定义、核心功能、架构设计、技术特点及应用案例，内容基于官方及权威来源，详实介绍该多智能体协作框架。

## 关键发现
- AutoGen 是微软研究院开源的多智能体协作框架，旨在快速构建复杂的 AI 应用。其核心思想是每个智能体（Agent）拥有不同角色（如开发者、执行者、规划者、分析师、工具调用者等），智能体间可自动对话协作完成复杂任务。  
来源：[CSDN博客 - AutoGen智能体框架教程](https://cancloud.blog.csdn.net/article/details/150931558)

- 核心功能包括模型管理、对话管理、工具调用、代码执行、记忆机制等，支持多角色对话系统、自动化任务执行、AI 编程助手、自动化数据分析等场景。  
来源：[CSDN博客 - AutoGen智能体框架教程](https://cancloud.blog.csdn.net/article/details/150931558)

- 架构设计采用事件驱动，分为三大核心层：Core（事件总线与运行时）、AgentChat（对话式智能体编排）、Extensions（模型与工具集成），支持本地单进程到分布式云端多语言多节点部署。配套开发者工具包括 AutoGen Studio 与 Bench。  
来源：[CSDN博客 - AutoGen框架深度解析](https://m.blog.csdn.net/fudaihb/article/details/147592849)

- 技术特点包括灵活的多智能体对话、内置丰富工具（浏览器代理、代码执行沙箱）、人机混合（Human-in-the-loop）、状态持久化与断点续跑、强大的可扩展性和调试能力。  
来源：[CSDN博客 - AutoGen框架深度解析](https://m.blog.csdn.net/fudaihb/article/details/147592849)

- 应用案例涵盖AI编程助手（代码生成与调试）、自动化数据分析（数据处理与可视化）、多角色专家顾问团队对话系统、自动化任务执行（API调用、脚本执行、工作流处理）等。  
来源：[CSDN博客 - AutoGen智能体框架教程](https://cancloud.blog.csdn.net/article/details/150931558)

## 证据与不确定性
调研内容基于微软官方开源项目及多篇权威技术博客，信息充分且一致。部分细节如最新版本特性和生态扩展仍需关注官方更新。

## 参考来源
- [AutoGen 智能体框架教程_autogen框架原理介绍-CSDN博客](https://cancloud.blog.csdn.net/article/details/150931558)
- [AutoGen 框架深度解析：构建多智能体协作的事件驱动架构-CSDN博客](https://m.blog.csdn.net/fudaihb/article/details/147592849)
- [AutoGen 详解:微软多智能体开发框架深度解析-CSDN博客](https://blog.csdn.net/weixin_47242663/article/details/149987921)
- [AutoGen框架入门:5个核心概念搭建智能体协作系统 - 博客园](https://www.cnblogs.com/deephub/p/19158962)
- [AutoGen 技术杂烩 - blog.iamdev.cn](https://blog.iamdev.cn/tags/AutoGen/)

已完成 /workspace/sources/findings_autogen.md 的写入。