"""
实体去重服务
识别并合并本地图谱中指代同一现实对象的冗余实体
"""

import json
from typing import List, Dict, Any, Set, Tuple, Optional
from app.utils import LLMClient
from .zep_entity_reader import EntityNode
from ..utils.logger import get_logger

logger = get_logger('mirofish.entity_deduplicator')

class EntityDeduplicator:
    """实体去重器"""

    def __init__(self, simulation_id: Optional[str] = None, project_id: Optional[str] = None):
        self.llm = LLMClient(simulation_id=simulation_id, project_id=project_id)

    def process(self, entities: List[EntityNode]) -> List[EntityNode]:
        """
        处理实体列表，进行去重和融合
        
        Args:
            entities: 原始实体列表
            
        Returns:
            去重后的实体列表
        """
        if not entities:
            return []

        logger.info(f"🔍 开始实体去重流程，原始实体数量: {len(entities)}")
        
        # 1. 记录原始实体
        original_names = [e.name for e in entities]
        logger.info(f"📋 原始实体名单: {original_names}")

        if len(entities) <= 1:
            return entities

        # 2. 调用 LLM 进行聚类识别
        clusters = self._identify_clusters(entities)
        
        if not clusters:
            logger.info("✅ 未发现重复实体，跳过融合步骤")
            return entities

        logger.info(f"🧠 LLM 识别出的聚类分组: {json.dumps(clusters, ensure_ascii=False)}")

        # 3. 按照聚类结果进行融合
        processed_uuids = set()
        final_entities = []
        
        # 建立名称到实体的映射
        name_to_entity = {e.name: e for e in entities}
        
        # 处理聚类中的实体
        for canonical_name, aliases in clusters.items():
            cluster_entities = []
            for name in aliases:
                if name in name_to_entity:
                    e = name_to_entity[name]
                    if e.uuid not in processed_uuids:
                        cluster_entities.append(e)
                        processed_uuids.add(e.uuid)
            
            if cluster_entities:
                if len(cluster_entities) > 1:
                    merged = self._merge_cluster(cluster_entities, canonical_name)
                    final_entities.append(merged)
                else:
                    final_entities.append(cluster_entities[0])

        # 处理未被聚类的剩余实体
        for e in entities:
            if e.uuid not in processed_uuids:
                final_entities.append(e)
        
        logger.info(f"🎯 去重完成: 最终保留 {len(final_entities)} 个实体")
        return final_entities

    def _identify_clusters(self, entities: List[EntityNode]) -> Dict[str, List[str]]:
        """调用 LLM 识别哪些名称是指代同一个实体的"""
        entity_info = []
        for e in entities:
            entity_info.append({
                "name": e.name,
                "type": e.get_entity_type(),
                "summary": e.summary[:100] if e.summary else ""
            })

        prompt = f"""
你是一个实体对齐（Entity Resolution）专家。请分析以下社交媒体模拟中的实体列表，识别出哪些名称实际上是指代同一个现实世界中的人、机构或对象。

## 待处理实体列表
{json.dumps(entity_info, ensure_ascii=False, indent=2)}

## 任务
1. 找出重复的实体（例如：“特朗普”和“Donald Trump”；“北大”和“北京大学”）。
2. 将它们分组成聚类。
3. 为每个聚类选定一个最规范的名称（Canonical Name）作为 Key。

## 输出格式 (必须是纯 JSON)
{{
    "Canonical Name 1": ["名称A", "名称B"],
    "Canonical Name 2": ["名称C", "名称D"]
}}
如果没有任何重复，请返回空对象 {{}}。
"""
        try:
            result = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": "你是一个精确的实体对齐专家。只返回 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                caller_hint="实体聚类识别"
            )
            return result
        except Exception as e:
            logger.error(f"❌ LLM 聚类失败: {e}")
            return {}

    def _merge_cluster(self, cluster: List[EntityNode], canonical_name: str) -> EntityNode:
        """融合一组冗余实体"""
        logger.info(f"🏗️ 正在融合聚类 [{canonical_name}]: {[e.name for e in cluster]}")
        
        # 选择 summary 最长的作为基础，因为它信息最丰富
        primary = max(cluster, key=lambda x: len(x.summary) if x.summary else 0)
        
        # 合并摘要
        summaries = [e.summary for e in cluster if e.summary and e.summary != primary.summary]
        if summaries:
            new_summary = f"{primary.summary}\n其他信息: " + " ".join(summaries)
        else:
            new_summary = primary.summary
            
        # 合并属性
        merged_attrs = primary.attributes.copy()
        merged_attrs["aliases"] = [e.name for e in cluster if e.name != canonical_name]
        
        # 合并关系
        all_edges = []
        seen_edges = set()
        for e in cluster:
            for edge in e.related_edges:
                # 简单的去重逻辑：基于边名称和目标
                edge_key = f"{edge.get('edge_name')}_{edge.get('target_node_uuid') or edge.get('source_node_uuid')}"
                if edge_key not in seen_edges:
                    all_edges.append(edge)
                    seen_edges.add(edge_key)
                    
        # 合并关联节点
        all_nodes = []
        seen_nodes = set()
        for e in cluster:
            for node in e.related_nodes:
                if node.get("uuid") not in seen_nodes:
                    all_nodes.append(node)
                    seen_nodes.add(node.get("uuid"))

        logger.info(f"✅ 融合完成: 选定主名称 [{primary.name}]，保留了 {len(all_edges)} 条关系")

        return EntityNode(
            uuid=primary.uuid, # 保留主 UUID
            name=canonical_name,
            labels=primary.labels,
            summary=new_summary,
            attributes=merged_attrs,
            related_edges=all_edges,
            related_nodes=all_nodes
        )
