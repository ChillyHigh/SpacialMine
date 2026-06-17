1. 不要默默兜底
代码出问题时，宁可明确失败，也不要偷偷 fallback。
silent fallback 最大的问题是：表面没报错，实际数据已经不可信了。
2. 测试失败时，先判断是谁错了
不要一看到 test fail 就立刻改代码。
先判断：是 production code 真的错了，还是测试本身设计不合理？
3. Prompt 不要写死在代码里
对于agent的项目，如果一个 prompt 会被长期维护，就应该放到 store、或者本地template / 配置里。
不要散落在代码逻辑中，不然后面很难改，也很难 review。
4. 接口就是契约
一个模块对外暴露什么、输入输出是什么、会抛什么错误，都应该清楚。
调用方不应该为了用一个模块，还必须去读它的内部实现。
5. 不要为了兼容而堆 shim
如果接口变了，就认真迁移调用方。
不要一直加临时兼容层，不然系统会越来越像补丁堆出来的。
6. 常量和共享配置只定义一次
重复出现的 magic value，应该抽到统一 config。
同一个东西散落在多个地方，迟早会改漏。
7. 避免循环依赖
模块之间要有清楚的依赖方向。
一旦互相 import，后面重构、测试、复用都会变得很痛苦。
8. 测试要按风险来做
不是每改一行都要跑全量测试。
小改动可以先 lint / typecheck / compile，大改动再跑相关测试。
9. 优先修 root cause
不要为了让测试过，随便放松 assertion。
测试变绿不代表问题解决了，有时候只是把问题藏起来了。
10. 不要随便加依赖
能不用新库就不用。
真的要加，也要说明为什么需要、影响范围是什么。
11. 错误只检查一次，不逐层堆叠
同一个前提条件不要在多层各自检查。如果 A 层已经校验了某个不变量，
B 层应默认相信并直接使用。逐层 raise 只会增加死代码和 review 负担，
不会提高安全性。
12. 函数名称应该简介明了，一般不宜超过4个单词，粗略表达意思即可。主要功能应写在注释里
13. 不要过度包装第三方错误
Minestudio、LangChain、vLLM 等库本身能明确报错时，项目层不要再包一层自定义异常。
这类异常应原样失败，避免增加无意义的错误转换和代码复杂度。
14. 不拆一次性短 helper
除了类对外接口、tool 函数、Handler run、PlanStore / ContextManager 等契约函数，
内部函数如果只被调用一次，且只是几行参数搬运、字符串拼接、简单条件判断，应直接内联。
不要定义只服务一处调用的过短辅助函数。
15. LLM 连接信息放在 .env
LLM model path、base url、API key 等信息必须从 .env 或运行环境变量读取。
尤其是 API key 不允许写进代码、prompt、文档示例默认值或配置对象。
缺少必需环境变量时让 KeyError / ValueError 原样失败，不写 silent fallback。
16. MineStudio 数据目录固定
创建 MinecraftSim 前必须设置：
os.environ.setdefault("MINESTUDIO_DIR", "/mnt/home/user42/ChillyHigh/minestudio_data")
该目录已经下载好 engine，不要让 check_engine 进入交互式下载流程。

本项目的内容是位于 ssh hitsz-ssh 服务器 /mnt/home/user42/ChillyHigh/SpacialMine/SpacialMine 的备份，ssh环境已经配置好uv环境，要运行需要在远程运行，本机不能运行
