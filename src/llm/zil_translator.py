"""On-demand ZIL translation utilities for game loop integration."""

import logging
from typing import Dict, Any, List, Optional, Union, Sequence

logger = logging.getLogger(__name__)


def _to_dict(entity: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    """Convert entity to dict, handling both dicts and Pydantic models.

    Args:
        entity: Entity as dict or Pydantic model

    Returns:
        Entity as dictionary
    """
    if isinstance(entity, dict):
        return entity

    # Handle Pydantic models
    if hasattr(entity, 'model_dump'):
        return entity.model_dump()

    # Fallback for other objects with __dict__
    if hasattr(entity, '__dict__'):
        return entity.__dict__

    return {}


def ensure_zil_translations(
    llm_client: Any,
    location: Optional[Union[Dict[str, Any], Any]] = None,
    items: Optional[Sequence[Any]] = None,
    npcs: Optional[Sequence[Any]] = None
) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Ensure all ZIL code in entities has been translated to natural language.

    This function checks entities for ZIL code and translates on-demand if
    no natural language description exists yet. Translations are cached
    and stored in the entity attributes.

    Args:
        llm_client: GeminiClient instance with translate_zil_with_cache method
        location: Optional location (dict or Pydantic model)
        items: Optional list of items (dicts or Pydantic models)
        npcs: Optional list of NPCs (dicts or Pydantic models)

    Returns:
        Tuple of (location_dict, items_dicts, npcs_dicts) with translations added
    """
    if not hasattr(llm_client, 'translate_zil_with_cache'):
        logger.warning("LLM client does not support ZIL translation")
        # Return dictified versions even if no translation
        location_dict = _to_dict(location) if location else None
        items_dicts = [_to_dict(item) for item in items] if items else []
        npcs_dicts = [_to_dict(npc) for npc in npcs] if npcs else []
        return location_dict, items_dicts, npcs_dicts

    # Translate location ZIL
    location_dict = None
    if location:
        location_dict = _to_dict(location)
        _translate_entity_zil(
            llm_client,
            location_dict,
            entity_type="location",
            entity_name=location_dict.get("name", location_dict.get("id", "unknown"))
        )

    # Translate item ZIL
    items_dicts = []
    if items:
        for item in items:
            item_dict = _to_dict(item)
            _translate_entity_zil(
                llm_client,
                item_dict,
                entity_type="item",
                entity_name=item_dict.get("name", item_dict.get("id", "unknown"))
            )
            items_dicts.append(item_dict)

    # Translate NPC ZIL
    npcs_dicts = []
    if npcs:
        for npc in npcs:
            npc_dict = _to_dict(npc)
            _translate_entity_zil(
                llm_client,
                npc_dict,
                entity_type="NPC",
                entity_name=npc_dict.get("name", npc_dict.get("id", "unknown"))
            )
            npcs_dicts.append(npc_dict)

    return location_dict, items_dicts, npcs_dicts


def _translate_entity_zil(
    llm_client,
    entity: Dict[str, Any],
    entity_type: str,
    entity_name: str
):
    """Translate ZIL code for a single entity if not already translated.

    Args:
        llm_client: GeminiClient instance
        entity: Entity dict (location, item, or NPC)
        entity_type: Type of entity for context
        entity_name: Name of entity for logging
    """
    # Ensure attributes dict exists and get reference to it
    if "attributes" not in entity:
        entity["attributes"] = {}
    attrs = entity["attributes"]

    # Translate main action routine
    if "zil_action_code" in attrs and "zil_action_description" not in attrs:
        zil_code = attrs["zil_action_code"]
        routine_name = attrs.get("zil_action", "unknown")

        try:
            logger.info(f"Translating {entity_type} '{entity_name}' action routine: {routine_name}")
            description = llm_client.translate_zil_with_cache(
                zil_code=zil_code,
                routine_name=routine_name,
                context=f"{entity_type} action for '{entity_name}'"
            )
            attrs["zil_action_description"] = description
            logger.debug(f"Translation: {description[:100]}...")
        except Exception as e:
            logger.error(f"Failed to translate ZIL for {entity_type} '{entity_name}': {e}")

    # Translate pseudo object routines (for locations with scenery)
    if entity_type == "location" and "zil_pseudo_routines" in attrs:
        if "zil_pseudo_descriptions" not in attrs:
            attrs["zil_pseudo_descriptions"] = {}

        for pseudo_name, routine_data in attrs["zil_pseudo_routines"].items():
            # Skip if already translated
            if pseudo_name in attrs["zil_pseudo_descriptions"]:
                continue

            zil_code = routine_data.get("zil_string", "")
            if not zil_code:
                continue

            try:
                logger.info(f"Translating pseudo object '{pseudo_name}' in location '{entity_name}'")
                description = llm_client.translate_zil_with_cache(
                    zil_code=zil_code,
                    routine_name=pseudo_name,
                    context=f"pseudo object (scenery) in '{entity_name}'"
                )
                attrs["zil_pseudo_descriptions"][pseudo_name] = description
            except Exception as e:
                logger.error(f"Failed to translate pseudo object '{pseudo_name}': {e}")


def translate_global_routines(
    llm_client,
    global_routines: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Translate all global routines that don't have descriptions yet.

    Args:
        llm_client: GeminiClient instance
        global_routines: Dict of routine_name -> routine_data

    Returns:
        Updated global_routines dict with translations
    """
    if not hasattr(llm_client, 'translate_zil_with_cache'):
        logger.warning("LLM client does not support ZIL translation")
        return global_routines

    for routine_name, routine_data in global_routines.items():
        # Skip if already translated
        if "description" in routine_data:
            continue

        zil_code = routine_data.get("zil_code", "")
        if not zil_code:
            continue

        try:
            logger.info(f"Translating global routine: {routine_name}")
            description = llm_client.translate_zil_with_cache(
                zil_code=zil_code,
                routine_name=routine_name,
                context="global game routine"
            )
            routine_data["description"] = description
        except Exception as e:
            logger.error(f"Failed to translate global routine '{routine_name}': {e}")

    return global_routines
