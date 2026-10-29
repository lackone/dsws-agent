### 注意事项

如果 ghcr.io/huggingface/text-embeddings-inference:cpu-latest 镜像拉取失败，可以

```
docker pull ghcr.nju.edu.cn/huggingface/text-embeddings-inference:cpu-latest

docker tag ghcr.nju.edu.cn/huggingface/text-embeddings-inference:cpu-latest ghcr.io/huggingface/text-embeddings-inference:cpu-latest
```

如果 elasticsearch 启动失败

```
chown -R 1000:1000 elasticsearch/data

docker compose up -d elasticsearch
```

如果 kibana 启动失败

```
chown -R 1000:1000 kibana/data

docker compose up -d kibana
```

如果 bge-large-zh-v1.5 模型下载失败

```
git clone https://www.modelscope.cn/BAAI/bge-large-zh-v1.5.git ./embedding/bge-large-zh-v1.5

docker compose up -d --force-recreate embedding
```

浏览器访问地址：

```
Qdrant 自带的 Dashboard，可直接查看 collection

http://192.168.0.111:6333/dashboard#/collections

Embedding 服务的接口文档页，可用来确认服务是否启动成功

http://192.168.0.111:8081/docs/

Kibana调试 Elasticsearch 的控制台入口

http://192.168.0.111:5601/app/elasticsearch/elasticsearch
```