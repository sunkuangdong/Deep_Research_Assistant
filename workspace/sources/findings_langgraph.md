# Findings: LangGraph
## 调研范围
本文件聚焦于LangGraph的定义、功能、技术架构和应用场景，重点涵盖其核心特点、技术实现、应用案例及优缺点，信息来源包括官方文档、技术博客及权威媒体报道。

## 关键发现
- LangGraph是由LangChain团队开发的一个开源框架，旨在帮助开发者构建基于大型语言模型(LLM)的复杂、有状态、多主体的应用。它通过将工作流表示为图结构(graph)，提供更高的灵活性和控制能力，特别适合需要循环逻辑、状态管理以及多主体协作的场景。  
来源：[博客园 - 折翼的小鸟先生](https://www.cnblogs.com/rpup)

- 技术架构上，LangGraph采用有向无环图(DAG)定义流程，核心概念包括节点(Node)、边(Edge)、状态(State)和图(Graph)，支持可视化、可控制和有状态的流程编排。框架提供add_node、add_edge等方法构建工作流，并支持条件分支。Agent的实现基于"工具调用+模型循环"的ReAct范式，包含ToolNode、状态管理等机制。  
来源：[CSDN - Thomas_Cai](https://devpress.csdn.net/user/ThomasCai001)

- LangGraph是LangChain生态组件的扩展，基于LangChain Expression Language (LCEL)的高级扩展，利用有向无环图协调多个LLM或状态，逻辑更清晰，适合复杂多步骤的LLM工作流。  
来源：[CSDN - LangGraph 入门与实战](https://m.blog.csdn.net/javastart/article/details/137019399)

- 应用场景包括构建多步骤的LLM工作流、实现复杂的Agent逻辑、状态管理和多主体协作，适用于需要灵活控制和状态传递的AI应用开发。  
来源：[博客园 - lightsong](https://www.cnblogs.com/lightsong/p/18811933)

- 优点：灵活的图结构工作流，支持状态管理和条件分支，适合复杂应用；基于开源生态，易于扩展和集成。  
- 缺点：相较于简单脚本，使用复杂度较高，学习曲线陡峭；依赖LangChain生态，脱离使用受限。  
来源：综合多篇技术博客

## 证据与不确定性
调研信息主要来自技术博客和社区文档，缺乏官方权威白皮书或详细技术文档，部分细节依赖社区实践经验总结，存在一定信息不完整和更新滞后的可能。

## 参考来源
- [折翼的小鸟先生 - 博客园](https://www.cnblogs.com/rpup)
- [LangGraph Platform - lightsong - 博客园](https://www.cnblogs.com/lightsong/p/18811933)
- [weixin_46994548 个人主页 - CSDN](https://devpress.csdn.net/user/weixin_46994548)
- [Thomas_Cai 个人主页 - CSDN](https://devpress.csdn.net/user/ThomasCai001)
- [LangGraph 入门与实战 - CSDN](https://m.blog.csdn.net/javastart/article/details/137019399)

已完成LangGraph的调研结果整理。