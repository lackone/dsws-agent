import os
from dataclasses import dataclass
from pathlib import Path

from omegaconf import OmegaConf


# 文件日志配置，对应 logging.file 这一组参数
@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


# 控制台日志配置，对应 logging.console 这一组参数
@dataclass
class Console:
    enable: bool
    level: str


# 把 file 和 console 两组日志配置再组合成 logging 总配置
@dataclass
class LoggingConfig:
    file: File
    console: Console


# 数据库配置
# 这里的结构既会给元数据库 db_meta 用，也会给数据仓库模拟库 db_dw 用
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int


# Embedding 服务配置，对应 YAML 里的 embedding 分组
@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str


# 本地 Embedding 配置，对应 YAML 里的 local_embedding 分组
# 开启后直接在本地进程内加载模型，不再访问远程推理接口
@dataclass
class LocalEmbeddingConfig:
    # 是否启用本地模型，启用后优先于远程接口
    enable: bool
    # 模型权重缓存目录，首次加载时框架会自动下载到这里
    cache_dir: str
    # HuggingFace 下载源地址，国内可换成 https://hf-mirror.com
    hf_endpoint: str
    # 运行设备，cpu 或 cuda
    device: str


# Elasticsearch 配置，对应 YAML 里的 es 分组
@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str


# 大模型配置，对应 YAML 里的 llm 分组
@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str


# AppConfig 是整个项目配置的总入口
# 这里的字段名，需要和 config.yaml 的顶层字段保持一致
@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    local_embedding: LocalEmbeddingConfig
    es: ESConfig
    llm: LLMConfig


# 从当前文件 app/conf/config.py 出发，回到项目根目录
# 再定位到 conf/config.yaml 这个配置文件
BASE_DIR = Path(__file__).resolve().parent.parent.parent
config_file = BASE_DIR / 'conf' / 'config.yaml'

# 读取 YAML 配置内容
context = OmegaConf.load(config_file)

# 根据 AppConfig 生成一份“结构化配置 schema”
schema = OmegaConf.structured(AppConfig)

# 把“配置结构”和“配置值”合并，再转换成真正可直接访问属性的对象
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

# 配置中的路径允许写成相对地址，统一按项目根目录解析成绝对路径
# 绝对路径原样保留，避免破坏已有的写法
cache_dir = Path(app_config.local_embedding.cache_dir)
if not cache_dir.is_absolute():
    cache_dir = BASE_DIR / cache_dir
app_config.local_embedding.cache_dir = str(cache_dir)

# 把 HuggingFace 下载源写入环境变量
# huggingface_hub 只在导入时读取该变量, 因此必须在本模块导入完成前设置
os.environ.setdefault("HF_ENDPOINT", app_config.local_embedding.hf_endpoint)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

# YAML 文件
#   -> OmegaConf.load 读取配置内容
#   -> OmegaConf.structured 准备配置结构
#   -> OmegaConf.merge 合并结构和内容
#   -> OmegaConf.to_object 转成配置对象

if __name__ == '__main__':
    # 简单测试：验证配置是否能正常读取
    print(app_config.es.host)