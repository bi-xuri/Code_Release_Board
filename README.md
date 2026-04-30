# 多仓库版本看板与固件下载平台

MVP 实现内容：

- 公开版本看板：项目列表、版本列表、版本详情、固件下载跳转
- 管理后台：JWT 登录、仓库配置 CRUD、手动同步、同步日志、下载日志
- Connector：GitHub、GitLab、Tencent CNB、Generic HTTP API、Manual 占位
- PostgreSQL 持久化，Redis 服务预留
- Docker Compose 一键启动

## 启动

```bash
cp .env.example .env
docker compose up --build
```

访问：

- 前台：http://localhost:8080
- 后台：http://localhost:8080/admin/login
- 默认管理员：admin / admin123
- 后端健康检查：http://localhost:8000/api/health

## GitHub 配置示例

- 仓库类型：GitHub
- 仓库地址：代码仓库网页地址，用于展示或跳转，例如 `https://github.com/openai/openai-python`
- API Base URL：留空或 `https://api.github.com`
- Owner / Group：`openai`
- Repo / Project：`openai-python`
- Access Token：私有仓库或高频调用时填写

## GitLab 配置示例

- 仓库类型：GitLab
- 仓库地址：代码仓库网页地址，用于展示或跳转，例如 `https://gitlab.com/gitlab-org/gitlab`
- API Base URL：留空或 `https://gitlab.com/api/v4`
- GitLab Project ID：数字 ID，或 `group/project`
- Access Token：私有仓库填写

## 新增仓库配置说明

后台“新增仓库”页面里的字段含义如下。

- 项目名称：后台展示名称，也是版本看板里的项目名称，建议填写便于识别的业务名称，例如 `OpenAI Python SDK`
- 仓库类型：决定使用哪种同步方式，目前支持 `GitHub`、`GitLab`、`Tencent CNB`、`Generic HTTP API`、`Manual Upload`
- 仓库地址：代码仓库或项目主页地址，主要用于展示、跳转和人工核对，不直接用于调用接口
- API Base URL：接口服务根地址，系统会基于它去请求版本数据；它和“仓库地址”不是一回事，前者给程序调用，后者给人看
- Owner / Group：仓库所属用户、组织或 GitLab Group，例如 GitHub 的 `openai`、GitLab 的 `gitlab-org`
- Repo / Project：仓库名或项目名，例如 GitHub 的 `openai-python`
- GitLab Project ID：仅 GitLab 常用，可填纯数字项目 ID，或 `group/project` 路径；当它已填写时，通常优先用它定位项目
- Access Token：访问私有仓库或提高接口限流时使用；系统会加密保存，编辑时留空表示保持原值不变
- 启用：关闭后仓库不会参与定时同步，通常也不作为有效数据源使用
- 同步频率：定时同步间隔，单位分钟，最小值是 `5`

### 仓库地址 和 API Base URL 的区别

- 仓库地址：仓库的网页地址，给管理员查看、跳转、核对来源用
- API Base URL：接口地址前缀，给后端程序拉取 Release、Tag、Asset 等数据用
- 典型情况：`GitHub` 的仓库地址是 `https://github.com/openai/openai-python`，API Base URL 是 `https://api.github.com`
- 典型情况：`GitLab` 的仓库地址是 `https://gitlab.com/gitlab-org/gitlab`，API Base URL 是 `https://gitlab.com/api/v4`
- 如果你接的是自建 GitLab、企业 GitHub Enterprise 或第三方系统，通常最需要改的是 `API Base URL`

### 各类型推荐填写方式

`GitHub`

- 仓库类型：`GitHub`
- 仓库地址：可填 `https://github.com/<owner>/<repo>`
- API Base URL：公网 GitHub 通常留空，或填 `https://api.github.com`
- Owner / Group：必填
- Repo / Project：必填
- GitLab Project ID：不填
- Access Token：私有仓库、企业仓库或接口频率高时建议填写

`GitLab`

- 仓库类型：`GitLab`
- 仓库地址：可填 `https://gitlab.com/<group>/<project>` 或自建 GitLab 对应地址
- API Base URL：公网 GitLab 通常留空，或填 `https://gitlab.com/api/v4`
- Owner / Group：使用 `group/project` 方式时可填写 group，便于识别
- Repo / Project：可填写 project 名称，便于识别
- GitLab Project ID：建议填写；可填数字 ID，或 `group/project`
- Access Token：私有项目通常必填

`Tencent CNB`

- 仓库类型：`Tencent CNB`
- 仓库地址：建议填写完整 Git 地址，例如 `https://cnb.cool/<group>/<repo>.git`
- API Base URL：不需要填写
- Owner / Group：可选；如果没填仓库地址，可与 `Repo / Project` 一起用来拼接地址
- Repo / Project：可选；与 `Owner / Group` 组合后会自动生成 `https://cnb.cool/<group>/<repo>.git`
- GitLab Project ID：不填
- Access Token：私有仓库必填，填写 CNB 个人访问令牌；公开仓库可留空
- 同步机制：当前按 Git Tags 同步版本，不依赖 CNB Release API
- 限制说明：当前不会自动抓取 Release 附件或固件文件，只同步 tag 作为版本记录

`Generic HTTP API`

- 仓库类型：`Generic HTTP API`
- 仓库地址：填项目主页或下载页地址，便于展示
- API Base URL：必填，填写第三方接口根地址
- Owner / Group`、`Repo / Project`、`GitLab Project ID`：是否填写取决于你的接口实现；如果当前接入逻辑未使用，可以留空
- Access Token：接口鉴权需要时填写

`Manual Upload`

- 当前代码里还是占位能力，没有完整上传流程
- 这类仓库建议先只作为预留配置，不要依赖它完成正式发布流程

### CNB 配置示例

- 项目名称：`demo-firmware`
- 仓库类型：`Tencent CNB`
- 仓库地址：`https://cnb.cool/acme/demo-firmware.git`
- API Base URL：留空
- Owner / Group：`acme`
- Repo / Project：`demo-firmware`
- GitLab Project ID：留空
- Access Token：私有仓库填写你的 CNB Token，公开仓库可留空

### CNB 同步规则

- 系统通过 `git ls-remote --tags` 读取 CNB 仓库里的 Git Tags
- 每个 tag 会被同步成一个版本，例如 tag `v1.2.3` 会生成版本 `v1.2.3`
- 包含 `alpha`、`beta`、`rc`、`preview` 的 tag 会标记为预发布版本
- 当前版本来源于 tag，不依赖 CNB 页面里的 Release 概念
- 当前不自动生成附件下载链接；如果你们的固件产物在别的制品库，建议后续再补下载规则或对接 Generic API
