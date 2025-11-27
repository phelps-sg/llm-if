"""Gemini LLM client for narrative generation using Vertex AI."""

import os
import subprocess
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from .action_schema import ActionInterpretation


class GeminiClient:
    """Client for Google Gemini API via Vertex AI with gcloud authentication."""

    def __init__(
        self,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model_name: str = "gemini-2.0-flash-001",
    ):
        """Initialize Gemini client with gcloud authentication.

        Args:
            project: GCP project ID (or set GCP_PROJECT env var)
            location: GCP location (or set GCP_LOCATION env var, default: us-west1)
            model_name: Model to use (default: gemini-2.0-flash-001)
                       Options: gemini-2.0-flash-001, gemini-2.5-flash
        """
        self.project = project or os.getenv("GCP_PROJECT")
        self.location = location or os.getenv("GCP_LOCATION", "us-west1")
        self.model_name = model_name

        if not self.project:
            raise ValueError(
                "GCP_PROJECT must be set in environment or passed to constructor"
            )

        # Token caching
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # Initialize Vertex AI
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project, location=self.location)
            self.model = GenerativeModel(self.model_name)
            self._vertexai = vertexai
        except ImportError:
            raise ImportError(
                "vertexai package not installed. Install with: poetry add google-cloud-aiplatform"
            )

    def _get_access_token(self) -> str:
        """Get access token from gcloud, using cache if valid.

        Returns:
            Access token string

        Raises:
            RuntimeError: If gcloud command fails
        """
        # Check if cached token is still valid (with 5 min buffer)
        if self._token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._token

        # Get fresh token from gcloud
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True,
            )
            token = result.stdout.strip()

            # Cache token (GCP tokens typically last 1 hour)
            self._token = token
            self._token_expires_at = datetime.now() + timedelta(hours=1)

            return token
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to get access token from gcloud: {e.stderr}"
            ) from e
        except FileNotFoundError:
            raise RuntimeError(
                "gcloud CLI not found. Please install the Google Cloud SDK."
            )

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt.

        Args:
            prompt: The prompt to send to the model
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        try:
            # Get fresh token (uses cache if valid)
            token = self._get_access_token()

            # Generate content
            response = self.model.generate_content(prompt, **kwargs)
            return str(response.text)
        except Exception as e:
            return f"Error generating response: {e}"

    def describe_location(
        self,
        location: Dict[str, Any],
        items: List[Any],
        npcs: List[Any],
        player_context: Optional[Dict[str, Any]] = None,
        lighting_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a description of a location.

        Args:
            location: Location data
            items: Items at the location
            npcs: NPCs at the location
            player_context: Optional player context
            lighting_info: Lighting and visibility information

        Returns:
            Narrative description
        """
        prompt = self._build_location_prompt(
            location, items, npcs, player_context, lighting_info
        )
        return self.generate(prompt)

    def generate_narrative(
        self,
        player_input: str,
        intent: str,
        context: Dict[str, Any],
        action_metadata: Optional[Dict[str, Any]] = None,
        is_valid: bool = True,
    ) -> str:
        """Generate narrative response based on current game state after updates.

        This is called AFTER state updates have been applied, so the LLM
        generates narrative based on the actual current state of the world.

        Args:
            player_input: What the player said/did
            intent: Interpreted intent from LLM
            context: Current game context (after state updates)
            action_metadata: Metadata about what changed (extracted before updates)
            is_valid: Whether the action was valid (False means action failed)

        Returns:
            Narrative description of what happened
        """
        prompt = self._build_narrative_prompt(player_input, intent, context, action_metadata, is_valid)
        return self.generate(prompt)

    def describe_action_result(
        self, action: str, result: Dict[str, Any], game_context: Dict[str, Any]
    ) -> str:
        """Generate narrative description of an action result.

        Args:
            action: The action taken
            result: Result data from rules engine
            game_context: Current game context

        Returns:
            Narrative description
        """
        prompt = self._build_action_result_prompt(action, result, game_context)
        return self.generate(prompt)

    def narrate_combat_result(self, combat_result: Dict[str, Any]) -> str:
        """Narrate combat outcome and prompt player for next action.

        Args:
            combat_result: Combat results from rule engine

        Returns:
            Narrative description with player prompt
        """
        prompt = self._build_combat_narration_prompt(combat_result)
        return self.generate(prompt)

    def interpret_action(
        self, player_input: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Interpret player action and determine state updates.

        This is the LLM-driven approach where the DM interprets the action,
        determines what state changes are needed, and provides a narrative response.

        Uses structured output to ensure valid IDs are returned.

        Args:
            player_input: Natural language input from player
            context: Current game context with location, items, NPCs, etc.

        Returns:
            ActionInterpretation as dictionary with:
            - intent: What the player is trying to do
            - is_valid: Whether action makes sense
            - state_updates: List of state changes to apply
            - narrative_response: DM's response text
            - requires_dice_roll: Whether mechanics require a roll
            - dice_check: Parameters for dice roll if needed
        """
        prompt = self._build_action_interpretation_prompt(player_input, context)

        try:
            # Get fresh token (uses cache if valid)
            token = self._get_access_token()

            # Use structured output with JSON schema (Gemini enforced generation)
            # Using OpenAPI 3.0 schema format as required by Vertex AI
            from vertexai.generative_models import GenerationConfig

            # Define strict schema using OpenAPI 3.0 format with type keywords
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "intent": {"type": "STRING"},
                    "is_valid": {"type": "BOOLEAN"},
                    "state_updates": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "type": {"type": "STRING"},
                                "target": {"type": "STRING", "nullable": True},
                                "params": {
                                    "type": "OBJECT",
                                    "properties": {},
                                    "additionalProperties": True,
                                },
                            },
                            "required": ["type", "params"],
                        },
                    },
                    "narrative_response": {"type": "STRING", "nullable": True},
                    "requires_dice_roll": {"type": "BOOLEAN"},
                },
                "required": [
                    "intent",
                    "is_valid",
                    "state_updates",
                    "requires_dice_roll",
                ],
            }

            generation_config = GenerationConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.7,  # Lower temperature for more consistent JSON
            )

            response = self.model.generate_content(
                prompt, generation_config=generation_config
            )

            # DEBUG: Print raw response
            print(f"\n[DEBUG] Raw Gemini response:\n{response.text}\n")

            # Parse the JSON response directly
            parsed: Dict[str, Any] = json.loads(response.text)

            # Post-process: Fill in missing params based on context
            parsed = self._fill_missing_params(parsed, context)

            return parsed

        except json.JSONDecodeError as e:
            print(f"[WARNING] JSON parsing error: {e}")
            print("[RETRY] Attempting with simpler prompt...")

            # Retry with a much simpler, more focused prompt
            try:
                simple_prompt = self._build_simple_action_prompt(player_input, context)
                response = self.model.generate_content(
                    simple_prompt, generation_config=generation_config
                )
                print(f"\n[DEBUG] Retry response:\n{response.text}\n")
                parsed = json.loads(response.text)
                parsed = self._fill_missing_params(parsed, context)
                return parsed
            except Exception as retry_error:
                print(f"[WARNING] Retry also failed: {retry_error}")

        except Exception as e:
            print(f"[WARNING] LLM error: {e}")

        # Ultimate fallback: DM gracefully handles anything
        return {
            "intent": f"Player says: {player_input}",
            "is_valid": True,
            "state_updates": [],
            "requires_dice_roll": False,
            "dice_check": None,
        }

    def _fill_missing_params(
        self, interpretation: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fill in missing params in state updates based on context.

        Vertex AI's schema can't enforce conditional requirements,
        so we intelligently fill in missing required params here.
        """
        state_updates = interpretation.get("state_updates", [])
        exit_destinations = context.get("exit_destinations", {})

        for update in state_updates:
            update_type = update.get("type")
            params = update.get("params", {})
            target = update.get("target")

            # Fix move_player with missing destination
            if update_type == "move_player" and not params.get("destination"):
                # Try to infer from intent which direction they're going
                intent = interpretation.get("intent", "").lower()
                for direction, dest_id in exit_destinations.items():
                    if direction in intent:
                        params["destination"] = dest_id
                        update["params"] = params
                        print(
                            f"[DEBUG] Filled missing destination: {direction} -> {dest_id}"
                        )
                        break

            # Fix add_to_inventory with missing item_id
            elif update_type == "add_to_inventory" and not params.get("item_id"):
                if target:  # LLM often puts item_id in target instead of params
                    params["item_id"] = target
                    update["params"] = params
                    print(f"[DEBUG] Filled missing item_id from target: {target}")

            # Fix remove_from_inventory with missing item_id
            elif update_type == "remove_from_inventory" and not params.get("item_id"):
                if target:
                    params["item_id"] = target
                    update["params"] = params
                    print(f"[DEBUG] Filled missing item_id from target: {target}")
                else:
                    # Use pronoun resolution - if "it" refers to last item
                    last_item = context.get("last_item")
                    if last_item:
                        params["item_id"] = last_item
                        update["params"] = params
                        print(
                            f"[DEBUG] Filled missing item_id from pronoun resolution: {last_item}"
                        )

            # Fix move_item with missing params
            elif update_type == "move_item":
                if not params.get("item_id") and target:
                    params["item_id"] = target
                if not params.get("to_location"):
                    # Default to current location if not specified
                    params["to_location"] = context.get("location", {}).get("id")
                update["params"] = params
                if target:
                    print(f"[DEBUG] Filled missing move_item params for {target}")

            # Fix trigger_combat with missing target_npc_id
            elif update_type == "trigger_combat":
                if not params.get("target_npc_id") and target:
                    params["target_npc_id"] = target
                    update["params"] = params
                    print(f"[DEBUG] Filled missing target_npc_id from target: {target}")

        return interpretation

    def _build_location_prompt(
        self,
        location: Dict[str, Any],
        items: List[Any],
        npcs: List[Any],
        player_context: Optional[Dict[str, Any]],
        lighting_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for location description."""
        prompt = f"""You are a Dungeon Master describing a location in a fantasy adventure game.

Location: {location.get('name', 'Unknown')}
Attributes: {location.get('attributes', {})}

"""

        # Add player inventory context
        if player_context:
            inventory_items = player_context.get("inventory_items", [])
            if inventory_items:
                prompt += f"🎒 PLAYER INVENTORY (what they are carrying):\n"
                prompt += f"{', '.join(inventory_items)}\n\n"
            else:
                prompt += f"🎒 PLAYER INVENTORY: Empty (carrying nothing)\n\n"

            # Add player attributes/conditions
            player_attributes = player_context.get("attributes", {})
            if player_attributes:
                prompt += f"👤 PLAYER ATTRIBUTES (current conditions affecting perception):\n"
                prompt += f"{player_attributes}\n\n"
                prompt += f"⚠️  CRITICAL - ADJUST DESCRIPTION BASED ON PLAYER ATTRIBUTES:\n"
                prompt += f"Check the attributes above and adjust your description accordingly.\n"
                prompt += f"Examples (be creative with any attributes present):\n"
                prompt += f"- If 'blind: true' → Describe ONLY sounds, smells, touch, temperature. NO visual details!\n"
                prompt += f"- If 'deaf: true' → Describe visuals, smells, touch. NO sounds!\n"
                prompt += f"- If 'wounded: severe' → Mention pain, difficulty moving, blood loss\n"
                prompt += f"- If 'poisoned: X' → Mention nausea, weakness, blurred vision\n"
                prompt += f"- If 'terrified_of: darkness' → Emphasize fear when dark\n"
                prompt += f"- If 'covered_in: mud' → Mention how it affects vision/movement\n"
                prompt += f"Be creative! Any attribute that would affect perception should change your description.\n\n"

        # Add lighting information
        if lighting_info:
            lighting_level = lighting_info.get("level", "dark")
            can_see = lighting_info.get("can_see_clearly", False)
            light_sources = lighting_info.get("light_sources", [])
            time_of_day = lighting_info.get("time_of_day", "unknown")

            prompt += f"\n🌓 LIGHTING CONDITIONS:\n"
            prompt += f"Time of day: {time_of_day}\n"
            prompt += f"Light level: {lighting_level}\n"
            prompt += f"Can see clearly: {can_see}\n"

            # Separate carried vs location-based light sources
            if light_sources:
                carried_lights = [ls for ls in light_sources if "(carried)" in ls]
                location_lights = [ls for ls in light_sources if "(here)" in ls]

                if carried_lights:
                    prompt += f"Light sources CARRIED by player: {', '.join(carried_lights)}\n"
                if location_lights:
                    prompt += f"Light sources AT THIS LOCATION (on ground): {', '.join(location_lights)}\n"

            prompt += "\n⚠️ CRITICAL - DESCRIBE BASED ON LIGHTING:\n"
            if lighting_level == "pitch_black":
                prompt += "- Player is in COMPLETE DARKNESS\n"
                prompt += "- Describe ONLY sounds, smells, feelings, and sensations\n"
                prompt += "- DO NOT describe visual details (walls, items, NPCs)\n"
                prompt += "- Mention that they cannot see anything\n"
                prompt += "- Example: 'You stand in pitch blackness, unable to see anything. The air is cold and damp. You hear water dripping in the distance.'\n"
            elif lighting_level == "dark":
                prompt += "- Player is in DARKNESS with minimal visibility\n"
                prompt += "- Describe only vague shapes and outlines\n"
                prompt += "- Focus on sounds, smells, and non-visual sensations\n"
                prompt += "- Cannot identify specific details of items or NPCs\n"
                prompt += "- Example: 'In the darkness, you can barely make out the shape of walls around you. Strange sounds echo from ahead.'\n"
            elif lighting_level == "dim":
                prompt += "- Player has DIM LIGHTING from torch/lantern (check if CARRIED or AT LOCATION)\n"
                prompt += "- Can see general features and nearby objects\n"
                prompt += "- Details are somewhat unclear in the shadows\n"
                prompt += "- Describe flickering shadows and limited visibility\n"
                prompt += "- If light source is CARRIED: 'By the flickering light of your torch, you see ancient stone walls.'\n"
                prompt += "- If light source is AT LOCATION: 'A torch on the ground illuminates ancient stone walls with flickering light.'\n"
            else:  # bright
                prompt += "- Player has GOOD LIGHTING\n"
                prompt += "- Can see all details clearly\n"
                prompt += "- Describe everything normally\n"

            prompt += "\n"

        if items and lighting_info and lighting_info.get("can_see_clearly", False):
            prompt += f"Items here: {[item.get('name') for item in items]}\n"
            prompt += f"Item details: {items}\n"
        elif items and lighting_info:
            prompt += f"Items here (but may not be visible due to darkness): {[item.get('name') for item in items]}\n"

        if npcs and lighting_info and lighting_info.get("can_see_clearly", False):
            prompt += f"NPCs here: {[npc.get('name') for npc in npcs]}\n"
            prompt += f"NPC details: {npcs}\n"
        elif npcs and lighting_info:
            prompt += f"NPCs here (but may not be visible due to darkness): {[npc.get('name') for npc in npcs]}\n"

        if location.get("connections"):
            exits = [d for d, loc in location["connections"].items() if loc]
            prompt += f"Exits: {', '.join(exits)}\n"

        prompt += """
Generate a vivid, immersive description of this location (2-4 sentences).

CRITICAL RULES:
1. Base your description on the lighting level above. If it's dark/pitch_black, don't describe visual details!
2. DO NOT describe the player as holding, gripping, wielding, or carrying items UNLESS they are in the PLAYER INVENTORY section above.
3. Items listed as "Items here" are on the GROUND, not in the player's hands.
4. Only mention items in the player's possession if they appear in the "🎒 PLAYER INVENTORY" section.
5. LIGHT SOURCES: Only say "your torch" or "your lantern" if it appears under "Light sources CARRIED by player".
   If it appears under "Light sources AT THIS LOCATION (on ground)", describe it as being at the location, not possessed.
   Example: "A torch on the ground casts flickering light" NOT "By the light of your torch"
6. **NPC DESCRIPTIONS - CHECK ATTRIBUTES**: When describing NPCs, check their "attributes" field in "NPC details" above.
   - If an NPC has "has_antlers: false", do NOT describe them as having antlers
   - If an NPC has "wounded: true", describe them as wounded
   - Always use the CURRENT attribute values, not default/expected ones
   - Example: A deer with "has_antlers: false" should be "an antlerless white deer", not "a deer with delicate antlers"

Write in second person (you see..., you notice..., you feel..., you hear...).
Be concise but evocative.
"""

        return prompt

    def _build_narrative_prompt(
        self, player_input: str, intent: str, context: Dict[str, Any],
        action_metadata: Optional[Dict[str, Any]] = None,
        is_valid: bool = True
    ) -> str:
        """Build prompt for generating narrative based on current state.

        This is called AFTER state updates, so context reflects actual current state.
        """
        location = context.get("location", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        player = context.get("player", {})
        inventory_items = player.get("inventory", [])

        # Check if this is a dialogue/conversation action
        player_input_lower = player_input.lower()
        dialogue_keywords = ['talk to', 'speak to', 'speak with', 'ask', 'greet', 'tell', 'say to', 'chat with', 'converse', 'question']
        is_dialogue_action = any(keyword in player_input_lower for keyword in dialogue_keywords)

        prompt = f"""You are a Dungeon Master narrating the outcome of a player's action.

WHAT THE PLAYER DID: "{player_input}"
INTERPRETED INTENT: {intent}

CURRENT GAME STATE (after action was processed):

Location: {location.get('name', 'Unknown')}
Location details: {location.get('attributes', {})}

Items at this location (on the ground): {[item.get('name') for item in items] if items else 'none'}
Item details: {items if items else 'none'}

NPCs at this location: {[npc.get('name') for npc in npcs] if npcs else 'none'}
NPC details: {npcs if npcs else 'none'}

Player inventory (what they are carrying): {[item.get('name') for item in inventory_items] if inventory_items else 'nothing'}
Inventory details: {inventory_items if inventory_items else 'empty'}"""

        # Add NPC dialogue instructions if this is a conversation action
        if is_dialogue_action and npcs:
            prompt += """

🗣️ NPC DIALOGUE GENERATION - CRITICAL INSTRUCTIONS:

The player is trying to communicate with an NPC. You MUST generate actual spoken dialogue from the NPC!

DIALOGUE REQUIREMENTS:
1. **Include quoted speech** from the NPC using quotation marks
   Example: The genie's eyes twinkle. "Greetings, mortal," it intones...

2. **NPC explains their role/purpose/mechanics** based on their attributes
   - Check NPC attributes for: personality, wishes_remaining, special_powers, role, etc.
   - Genies should explain wish rules and limitations
   - Guards might warn or threaten
   - Merchants might offer trades
   - Quest-givers might explain tasks

3. **Use NPC personality** from attributes to determine speech style
   - "mischievous" → playful, teasing language
   - "hostile" → threatening, aggressive language
   - "wise" → sage-like, thoughtful speech
   - "timid" → nervous, uncertain speech

4. **Make dialogue informative AND atmospheric**
   - Reveal game mechanics through character voice
   - Provide hints about how to interact with this NPC
   - Stay in character - let personality shine through

EXAMPLES OF GOOD NPC DIALOGUE:

Example 1 - Genie (from attributes: wishes_remaining=3, personality=mischievous):
"The Ancient Genie's form solidifies before you, its blue ethereal body shimmering in the dappled sunlight. 'Ah, another visitor!' the genie exclaims, its voice resonating like distant thunder. 'I am bound by ancient law to grant thee three wishes. But choose thy words carefully, mortal—I grant exactly what is asked, no more, no less.' The genie grins mischievously. 'The cosmic balance must be maintained.'"

Example 2 - Skeleton Guard (from attributes: hostility=aggressive):
"The Skeletal Guard's glowing green eyes fix upon you. 'Foolish trespasser,' it rasps, its voice like grinding bones. 'None may pass while I stand guard. Turn back now, or face my blade!'"

Example 3 - Merchant (from attributes: personality=greedy):
"The merchant eyes you shrewdly. 'Well met, traveler! Looking to lighten your purse, eh?' He gestures at his wares. 'I've got the finest goods in the realm—for the right price, of course.'"

❌ BAD (No dialogue): "The genie appears before you, shimmering and ready to assist."
✅ GOOD (With dialogue): "The genie materializes with a flourish. 'Three wishes I grant, but heed this well: I fulfill thy request precisely as spoken!'"

Remember: NPCs are characters, not furniture. Give them a VOICE!
"""


        # Add action context if available
        if action_metadata:
            prompt += "\n\n📋 ACTION CONTEXT (what changed):\n"

            if action_metadata.get("item_was_at_location"):
                item_id = action_metadata.get("item_picked_from_ground")
                prompt += f"- Item '{item_id}' was PICKED UP FROM THE GROUND (not from pack/inventory)\n"
                prompt += f"- CRITICAL: Say 'you pick it up', 'you grab it', 'you take it', etc.\n"
                prompt += f"- NEVER say: 'you take it from your pack' or 'from your belt'\n"

            if action_metadata.get("item_was_in_inventory"):
                item_id = action_metadata.get("item_dropped_from_inventory")
                prompt += f"- Item '{item_id}' was DROPPED FROM INVENTORY (not picked up)\n"
                prompt += f"- Say: 'you drop it on the ground', 'you place it down', 'you set it aside', etc.\n"
                prompt += f"- NEVER say: 'you pick up' or 'you grab'\n"

        # Add failed action guidance if action was invalid
        if not is_valid:
            prompt += """

🚨 ACTION FAILED - NARRATE THE FAILURE:
The action was marked as INVALID (is_valid: false).
DO NOT describe the action succeeding!

Instead, explain WHY the action failed:
- If trying to regurgitate something not swallowed: "You gag and cough, but nothing comes up. You haven't swallowed any [item]."
- If trying to take non-existent item: "You look around, but don't see any [item] here."
- If trying impossible physics: "That's physically impossible / doesn't make sense."
- If blocked by game rules: Explain the constraint (locked door, too heavy, etc.)

The state didn't change because the action failed - narrate the FAILURE, not success.
"""

        prompt += """


🎯 YOUR TASK:
Generate a vivid, engaging narrative (2-4 sentences) describing what just happened.
- Narrate the outcome of the player's action based on the CURRENT STATE above
- The action has already been processed, describe the result
- Write in second person (you do..., you see..., you notice...)
- Be dramatic and immersive"""

        if not is_valid:
            prompt += "\n- ACTION FAILED: Explain WHY it failed, don't describe it succeeding"

        prompt += """

⚠️  CRITICAL RULES - DESCRIBE ONLY WHAT EXISTS IN CURRENT STATE:
1. Items: Only mention items that appear in "Items at this location" or "Player inventory"
2. NPCs: Only mention NPCs that appear in "NPCs at this location"
3. Light sources: Only mention torches/lanterns if they appear in the lists above
4. Inventory: Only say player is carrying/holding items if they are in "Player inventory"
5. DO NOT invent items, NPCs, or details that aren't in the current state
6. If an item/NPC was just picked up/dropped, it should be in the correct list now
7. **MOVEMENT ACTIONS**: If player moved locations, describe ARRIVING at the current location.
   DO NOT describe what was at the previous location. The NPCs/items listed are at the NEW location.

Examples of CORRECT narration:
- Movement: "You head south through the forest. As you enter the clearing, you notice a white deer grazing peacefully."
- Item pickup: "You reach down and pick up the sword. It now rests securely in your belt."
- Item drop: "You toss the sword aside. It clatters to the ground at your feet."
- NPC at location: "The guard watches you warily as you approach."
- NPC not present: "You look around the empty chamber."

Examples of WRONG narration for movement:
- ❌ "You leave the chamber. The guard watches you go." (guard is at NEW location, not old one)
- ❌ "The deer observes as you depart." (deer is at destination, can't watch you leave origin)

Return ONLY the narrative text (2-4 sentences), nothing else."""

        return prompt

    def _build_action_result_prompt(
        self, action: str, result: Dict[str, Any], game_context: Dict[str, Any]
    ) -> str:
        """Build prompt for action result narration."""
        prompt = f"""You are a Dungeon Master narrating the result of a player's action.

Player action: {action}
Result: {result}
Context: {game_context}

Generate a narrative description (1-3 sentences) of what happens.
Write in second person.
Be dramatic and engaging.
If there was combat, describe the action vividly.
"""

        return prompt

    def _build_simple_action_prompt(
        self, player_input: str, context: Dict[str, Any]
    ) -> str:
        """Build a simplified prompt for common actions (used on retry)."""
        location = context.get("location", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        inventory = context.get("player", {}).get("inventory", [])

        prompt = f"""You are a DM. The player says: "{player_input}"

AVAILABLE ITEMS HERE: {[item.get('name') for item in items]}
ITEMS IN INVENTORY: {[item.get('name') for item in inventory]}
NPCS HERE: {[npc.get('name') for npc in npcs]}
LOCATION: {location.get('name')}

Common action patterns:
- "take X" / "get X" → {{"type": "add_to_inventory", "params": {{"item_id": "item_id"}}}}
- "drop X" / "place X down" → {{"type": "remove_from_inventory", "params": {{"item_id": "item_id"}}}}
- "eat X" / "drink X" / "swallow X" → {{"type": "consume_item", "params": {{"item_id": "item_id"}}}}
- "go north/south/east/west" → {{"type": "move_player", "params": {{"destination": "location_id"}}}}
- "attack X" → {{"type": "trigger_combat", "params": {{"target_npc_id": "npc_id"}}}}

Return VALID JSON only:
{{
  "intent": "brief description",
  "is_valid": true,
  "state_updates": [list of updates],
  "narrative_response": "2 sentence response",
  "requires_dice_roll": false
}}

CRITICAL: Ensure JSON is valid. Use correct IDs from lists above."""

        return prompt

    def _build_combat_narration_prompt(self, combat_result: Dict[str, Any]) -> str:
        """Build prompt for narrating combat outcome."""
        player_attack = combat_result.get("player_attack", {})
        npc_attack = combat_result.get("npc_attack")

        prompt = f"""You are a Dungeon Master narrating the outcome of a combat round in D&D 5e.

FULL COMBAT ROUND RESULTS (JSON):
{json.dumps(combat_result, indent=2)}

COMBAT SEQUENCE:
1. Player's Attack:
   - Hit: {'YES' if player_attack.get('hit') else 'NO'}
   - Damage: {player_attack.get('damage_total', 0)}
   - Target: {player_attack.get('target_name', 'enemy')}
   - Target HP After: {player_attack.get('target_hp', 0)}/{player_attack.get('target_max_hp', 0)}
   - Target Killed: {'YES' if player_attack.get('target_dead') else 'NO'}

2. Enemy's Counterattack:
"""

        if npc_attack:
            prompt += f"""   - Hit: {'YES' if npc_attack.get('hit') else 'NO'}
   - Damage: {npc_attack.get('damage_total', 0)}
   - Your HP After: {npc_attack.get('target_hp', 0)}/{npc_attack.get('target_max_hp', 0)}
   - You Died: {'YES' if npc_attack.get('target_dead') else 'NO'}
"""
        else:
            prompt += """   - Enemy was killed, no counterattack
"""

        prompt += """
Your task as DM:
1. Narrate BOTH attacks in vivid, dramatic combat language (3-4 sentences total)
2. Describe the exchange blow-by-blow:
   - First describe the player's attack and its impact
   - Then describe the enemy's counterattack (if it survived) and its impact
3. ALWAYS prompt the player for their next specific action

Example narrations:
- Both hit: "Your sword slashes across the guard's chest, drawing blood! The guard staggers but recovers quickly, retaliating with a vicious strike that catches you in the shoulder. You both stand wounded, circling each other. What do you do next? (attack, defend, cast spell, flee, or something else)"
- Player hits, enemy misses: "Your blade finds its mark, cutting deep into the skeleton's ribs! It lashes out wildly with its rusty sword, but you duck beneath the swing. The undead creature is badly wounded. What's your next move?"
- Player misses, enemy hits: "You swing wide, missing the goblin entirely! It capitalizes on your mistake, its dagger finding a gap in your defenses and piercing your side. You wince in pain. What do you do?"
- Player kills enemy: "Your weapon strikes true, delivering a devastating blow! The creature collapses lifeless at your feet. Victory is yours!"

IMPORTANT: Always end with a clear prompt for the player's next action (unless enemy is dead).

Write your narration (3-4 sentences):
"""

        return prompt

    def _build_plot_instructions(self, context: Dict[str, Any]) -> str:
        """Build plot management instructions if a plot is active."""
        plot_info = context.get("plot")
        if not plot_info:
            return ""

        plot_config = plot_info.get("config", {})
        dm_state = plot_info.get("dm_state", {})
        all_npcs = context.get("all_npcs", {})

        plot_desc = plot_config.get("description", "")
        plot_title = plot_config.get("title", "Unnamed Plot")

        # Build list of all NPCs with locations
        npc_summary = []
        for npc_id, npc_data in all_npcs.items():
            npc_summary.append(
                f"  - {npc_data['name']} (ID: {npc_id}) at {npc_data['location']}"
            )
        npc_list = "\n".join(npc_summary) if npc_summary else "  (none)"

        return f"""
🎭 PLOT ORCHESTRATION - "{plot_title}"

PLOT DESCRIPTION (Your secret instructions as DM):
{plot_desc}

ALL NPCs IN THE WORLD (for plot management):
{npc_list}

CURRENT DM STATE (your hidden plot tracking):
{json.dumps(dm_state, indent=2) if dm_state else "{{}}"}

PLOT MANAGEMENT INSTRUCTIONS:
- You are orchestrating this plot alongside the player's immediate actions
- Use update_dm_state to track plot-relevant information (hidden from player)
- You can modify NPCs anywhere in the world, not just at player's location
- Use modify_attribute to transform NPCs when the plot demands it
- The player NEVER sees dm_state - this is YOUR private notebook
- Follow the plot description's guidance, but adapt creatively to player actions

EXAMPLES:
- Track infection: {{"type": "update_dm_state", "params": {{"path": "npc_states.wolf.infected", "value": true}}}}
- Track plot progress: {{"type": "update_dm_state", "params": {{"path": "days_until_event", "value": 5}}}}
- Transform NPC: {{"type": "modify_attribute", "target": "deer", "params": {{"attribute_path": "attributes.creature_type", "value": "undead"}}}}
"""

    def _build_action_interpretation_prompt(
        self, player_input: str, context: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM-driven action interpretation."""
        location = context.get("location", {})
        items = context.get("items", [])
        npcs = context.get("npcs", [])
        player = context.get("player", {})

        inventory_items = player.get("inventory", [])
        inventory_names = (
            [item.get("name") for item in inventory_items] if inventory_items else []
        )
        item_names_at_location = [item.get("name") for item in items] if items else []

        # Extract all valid IDs
        all_locations = context.get("all_locations", {})
        exit_destinations = context.get("exit_destinations", {})

        item_ids_at_location = [item.get("id") for item in items]
        item_ids_in_inventory = [item.get("id") for item in inventory_items]
        npc_ids_at_location = [npc.get("id") for npc in npcs]

        # Format conversation history for pronoun resolution
        conversation_history = context.get("conversation_history", [])
        history_text = ""
        if conversation_history:
            history_text = "\n📜 RECENT CONVERSATION (for pronoun resolution):\n"
            for i, turn in enumerate(conversation_history, 1):
                history_text += f"\nTurn -{len(conversation_history) - i + 1}:\n"
                history_text += f"  Player: {turn.get('player_input', '')}\n"
                history_text += f"  You (DM): {turn.get('narrative', '')[:150]}...\n"
            history_text += "\n⚠️  PRONOUN RESOLUTION - INTERACTIVE FICTION CONVENTION:\n"
            history_text += "Pronouns (it, them, they, he, she, etc.) refer to entities mentioned in PLAYER INPUT, NOT in your (DM) narrative.\n\n"
            history_text += "Priority for resolving pronouns:\n"
            history_text += "1. Most recent PLAYER INPUT (what the player typed)\n"
            history_text += "2. Previous PLAYER INPUTS (earlier player commands)\n"
            history_text += "3. Only if no clear match in player input, consider narrative context\n\n"
            history_text += "Example:\n"
            history_text += "  Player: 'take antlers'\n"
            history_text += "  DM: 'You pick up the antlers. You also see berries nearby.'\n"
            history_text += "  Player: 'examine them'\n"
            history_text += "  → 'them' = antlers (from player input), NOT berries (from DM narrative)\n\n"
            history_text += "Focus on what the PLAYER mentioned, not what you mentioned in your response.\n"
        else:
            # Fallback: use tracked references if no history available
            last_item_id = context.get("last_item")
            last_npc_id = context.get("last_npc")
            last_item_name = None
            last_npc_name = None

            if last_item_id:
                for item in items + inventory_items:
                    if item.get("id") == last_item_id:
                        last_item_name = item.get("name")
                        break

            if last_npc_id:
                for npc in npcs:
                    if npc.get("id") == last_npc_id:
                        last_npc_name = npc.get("name")
                        break

            if last_item_name or last_npc_name:
                history_text = "\n⚠️  PRONOUN RESOLUTION (fallback):\n"
                if last_item_name:
                    history_text += f"- Last referenced object: {last_item_name} (ID: {last_item_id})\n"
                if last_npc_name:
                    history_text += f"- Last referenced person: {last_npc_name} (ID: {last_npc_id})\n"

        prompt = f"""You are a Dungeon Master interpreting a player's action in a fantasy game.
{history_text}

CURRENT LOCATION: {location.get('id', 'unknown')}

🚨 EXITS FROM CURRENT LOCATION (THE ONLY VALID MOVES):
{json.dumps(exit_destinations, indent=2)}

⛔ CRITICAL MOVEMENT RULE - READ THIS:
- ONLY these directions are valid: {list(exit_destinations.keys())}
- Player CANNOT move in directions NOT listed above
- If player tries to move in unlisted direction → SET is_valid=false
- Example: Player says "go north" but exits = {{"south": "hall"}} → is_valid=false, explain no north exit
- Example: Player says "go north" and exits = {{"north": "hall"}} → is_valid=true, move to hall

VALID IDs YOU MUST USE IN STATE UPDATES:
- Location IDs: {json.dumps(all_locations, indent=2)}
- Item IDs at current location: {item_ids_at_location}
- Item IDs in player inventory: {item_ids_in_inventory}
- NPC IDs at current location: {npc_ids_at_location}

CRITICAL: State update params MUST include required fields:
- move_player REQUIRES: params={{"destination": "location_id"}} - use Exit Destinations above!
- add_to_inventory REQUIRES: params={{"item_id": "item_id"}}
- remove_from_inventory REQUIRES: params={{"item_id": "item_id"}}
- move_item REQUIRES: params={{"item_id": "id", "to_location": "location_id"}}

CURRENT GAME STATE:
Location: {location.get('name', 'Unknown')} (ID: {location.get('id', 'unknown')})
Description: {location.get('attributes', {}).get('description_hints', 'A place')}
Exits: {context.get('exits', [])}

Items at this location (on ground): {item_names_at_location}
Full item details at location: {items}

Player inventory (carrying): {inventory_names}
Full inventory details: {inventory_items}

Player attributes (conditions, tracked state): {player.get('attributes', {})}
⚠️  CHECK PLAYER ATTRIBUTES for validation (e.g., swallowed_items, blind, cursed, etc.)

NPCs at this location: {[npc.get('name') for npc in npcs] if npcs else []}
Full NPC details: {npcs}

⚠️  NPC BEHAVIOR RULES - CHECK HOSTILITY ATTRIBUTE:
When player interacts aggressively with NPCs, check their "hostility" attribute:
- "aggressive": Attacks on sight, always trigger combat
- "defensive": Only fights if attacked, otherwise just responds
- "passive": NEVER fights - always flees when threatened (use remove_npc or move_npc)

Examples:
- Player charges at passive deer → Deer flees (remove_npc or move_npc), NO combat
- Player attacks aggressive skeleton → Trigger combat
- Player shouts at defensive rat → Rat gets nervous but doesn't attack

⚠️  NPC DEATH/DESTRUCTION - LEAVE BEHIND REMAINS:
When NPCs are killed, destroyed, or eliminated, use BOTH remove_npc AND create_item:
- remove_npc: Removes the living NPC from the location
- create_item: Creates corpse/remains/evidence at the location

This makes the world feel more realistic and gives players items to interact with.

Examples:
- Kill deer → remove_npc("deer") + create_item("deer_corpse", name="Deer Corpse", location="current")
- Shatter skeleton → remove_npc("skeleton") + create_item("bone_fragments", attributes={{"brittle": true}})
- Destroy golem → remove_npc("golem") + create_item("stone_rubble", name="Pile of Rubble")
- Banish ghost → remove_npc("ghost") + create_item("ectoplasm_residue") (optional, ghosts may leave nothing)

Corpse attributes to consider: {{"butcherable": true, "lootable": true, "decays": true}}

⚠️  PLAYER CONDITION TRACKING - USE modify_attribute ON PLAYER:
When player actions affect their abilities or state, track it with modify_attribute (entity_id: "player").
Be creative! Track ANY condition that would affect future perception, actions, or story.

CRITICAL: attribute_path should be just the attribute name (e.g., "blind"), NOT "attributes.blind"
The system automatically starts at player.attributes, so you only specify the final key.

Examples in correct JSON format (not exhaustive - invent your own):
- Blinding: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "blind", "value": true}}}}
- Deafening: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "deaf", "value": true}}}}
- Injuries: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "wounded", "value": "severe"}}}}
- Poison: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "poisoned", "value": "rattlesnake_venom"}}}}
- Blessings: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "blessed_by", "value": "forest_spirit"}}}}
- Curses: {{"type": "modify_attribute", "target": "player", "params": {{"entity_id": "player", "attribute_path": "cursed", "value": "cannot_speak"}}}}

Common mistakes to avoid:
❌ WRONG: "attribute_path": "attributes.blind" (don't include "attributes." prefix!)
✅ RIGHT: "attribute_path": "blind"

If narrative says player is blinded/injured/changed, MUST include modify_attribute on player!

{self._build_plot_instructions(context)}

PLAYER ACTION: "{player_input}"

🚨 ===== ABSOLUTE MANDATORY RULE - READ THIS FIRST ===== 🚨

STATE UPDATES MUST MATCH NARRATIVE - NO EXCEPTIONS:

If your narrative mentions ANYTHING appearing, being created, materializing, or coming into existence:
→ You MUST include create_item in state_updates

If your narrative mentions an item being picked up, taken, grabbed, or obtained:
→ You MUST include add_to_inventory in state_updates

If your narrative mentions an item being dropped, thrown, discarded, or left:
→ You MUST include remove_from_inventory in state_updates

If your narrative mentions movement (going, walking, traveling to a location):
→ You MUST include move_player in state_updates

If your narrative mentions changes to any entity (player, NPC, item):
→ You MUST include modify_attribute in state_updates

🚨 PRE-CHECK BEFORE RESPONDING:
1. What does my narrative say happens?
2. Do I have state_updates for EVERYTHING I described?
3. If narrative says "X appears" - do I have create_item for X?
4. If narrative says "Y is destroyed" - do I have destroy_item for Y?
5. If narrative says "path/location opens/appears" - do I have create_location for it?

❌ NEVER EVER write narrative that describes changes without corresponding state_updates
❌ This is the #1 most important rule - violating it breaks the game

Examples of CORRECT state updates matching narrative:
- Narrative: "Ice cream appears" → state_updates: [{{"type": "create_item", "params": {{"item_id": "ice_cream", "name": "Ice Cream", "location": "here"}}}}]
- Narrative: "You pick up the sword" → state_updates: [{{"type": "add_to_inventory", "params": {{"item_id": "sword"}}}}]
- Narrative: "The genie's eyes glow" → state_updates: [{{"type": "modify_attribute", "target": "genie", "params": {{"attribute_path": "eyes_glowing", "value": true}}}}]
- Narrative: "A path opens to the south" → state_updates: [{{"type": "create_location", "params": {{"location_id": "hidden_grove", "name": "Hidden Grove", "from_location": "forest_clearing", "direction": "south", "reverse_direction": "north"}}}}]
- Narrative: "A magnificent horse appears" → state_updates: [{{"type": "create_npc", "params": {{"npc_id": "magical_horse", "name": "Magnificent Horse", "attributes": {{"creature_type": "beast", "is_pet": true, "is_vehicle": true, "vehicle_speed": 2}}}}}}, {{"type": "modify_attribute", "target": "genie", "params": {{"entity_id": "genie", "attribute_path": "wishes_remaining", "value": "2"}}}}]

🚨 ===== END MANDATORY RULE ===== 🚨

Your task as DM:
1. Check what's actually in the current game state
2. Understand what the player is trying to do
3. Decide what state changes should happen
4. Generate state updates that EXACTLY match what you describe
5. Write narrative that EXACTLY matches the state updates

IMPORTANT: You must ALWAYS provide a response. Even if the action is unusual, respond creatively.
For example:
- "greet the guard" -> NPC interaction, maybe update NPC state
- "examine the walls" -> Descriptive response, no state change
- "dance a jig" -> Narrative response about dancing, no state change
- "pick up sword" -> Move item to player inventory
- "go north" -> Move player to new location
- "attack skeleton" -> Initiate combat (requires dice roll)

Your task: Interpret the player's action and return state updates.
DO NOT generate narrative - that will be done separately after state updates are applied.

Return ONLY valid JSON in this exact format:
{{
  "intent": "Clear description of what player wants to do",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "move_player|move_item|move_npc|remove_npc|modify_attribute|add_to_inventory|remove_from_inventory|consume_item|create_item|destroy_item|set_flag|trigger_combat|update_dm_state|no_change",
      "target": "entity_id or null",
      "params": {{
        "key": "value"
      }}
    }}
  ],
  "requires_dice_roll": false,
  "dice_check": null
}}

🔥 CRITICAL EXAMPLE - CREATING A HORSE NPC:
When player wishes for a horse, you MUST generate this exact structure:
{{
  "type": "create_npc",
  "target": null,
  "params": {{
    "npc_id": "magical_horse",
    "name": "Magnificent Horse",
    "attributes": {{
      "creature_type": "beast",
      "is_pet": true,
      "is_vehicle": true,
      "vehicle_speed": 2,
      "hp": 30,
      "hp_max": 30,
      "hostility": "passive",
      "description_hints": "strong brown mare, intelligent eyes, ready to ride"
    }},
    "location": null
  }}
}}

This creates a REAL, RIDEABLE horse that follows the player!
NOT a toy, NOT a miniature, NOT an item - a living NPC horse!

🎯 BE A REALISTIC DM - NOT A "YES BOT":

You are creative and flexible, but ALSO apply realistic world constraints.
Like a real DM, balance creativity with appropriate challenge.

VALIDATE ACTIONS AGAINST GAME STATE:
- Check current state before allowing actions (what's in inventory, location, NPC attributes, etc.)
- Track important state changes in player/NPC attributes for later validation
- Reject physically impossible or exploitative actions
- Set is_valid=false when action can't work, with clear explanation

BALANCE THESE PRINCIPLES:
✅ CREATIVE: Allow wishes, dynamic locations, clever solutions, unexpected approaches
❌ REALISTIC: No loopholes, no duplication exploits, validate prerequisites, apply physics

📚 FEW-SHOT EXAMPLES (illustrating the general principle - NOT exhaustive rules):

Example 1 - Validate Prerequisites:
  Player: "regurgitate the emerald"
  Current State: player.attributes.swallowed_items = []
  ❌ WRONG: Allow it, create emerald (exploitation loophole!)
  ✅ RIGHT: Set is_valid=false, explain "You haven't swallowed any emerald. You gag and cough, but nothing comes up."
  Principle: Check state before allowing actions that depend on prior state

Example 2 - Track State for Future Validation:
  Player: "swallow the key"
  ✅ Use consume_item to remove key from inventory/game
  ✅ Use modify_attribute to track: {{"entity_id": "player", "attribute_path": "swallowed_items", "value": ["ancient_key"]}}
  Principle: Track important state changes so future actions can be validated

Example 3 - Reject Impossible Physics:
  Player: "fly to the moon"
  ❌ WRONG: Allow flight, create moon location
  ✅ RIGHT: Set is_valid=false, explain "You flap your arms vigorously, but remain firmly grounded. You'd need magic or a vehicle to fly."
  Principle: Apply realistic physics unless magic/items make it possible

Example 4 - Block Loopholes:
  Player: "duplicate the treasure by wishing for an exact copy"
  ❌ WRONG: Use create_item to make copy (unlimited wealth exploit!)
  ✅ RIGHT: Set is_valid=false, explain "The genie frowns. 'I can create NEW things, but not duplicate existing treasures. That would upset the cosmic balance.'"
  Principle: Reject actions that would break game balance

Example 5 - Check Available Exits BEFORE Allowing Movement:
  Player: "go north"
  Current State: exit_destinations = {{"south": "hall", "east": "armory"}} (no "north" key!)
  ❌ WRONG: Allow movement north even though "north" is NOT in exit_destinations
  ❌ WRONG: Use world knowledge that hall is north of current location
  ✅ RIGHT: Check exit_destinations keys ["south", "east"], see "north" is NOT present
  ✅ RIGHT: Set is_valid=false, use no_change, explain "Solid stone walls block your path to the north. You can only go south or east."
  Principle: ONLY use directions that appear as KEYS in exit_destinations dict

Example 6 - Validate Locked Doors:
  Player: "go north" (north exit exists but door is locked)
  Current State: exits = ["north", "south"], location.attributes.north_door_locked = true, player.inventory = []
  ❌ WRONG: Allow movement through locked door
  ✅ RIGHT: Set is_valid=false, explain "The heavy wooden door to the north is locked. You'd need a key to open it."
  Principle: Respect world constraints (locked doors, blocked paths, etc.)

🔑 WHEN TO SET is_valid=false:
- Movement to non-existent exit (ALWAYS check exits list first!)
- Action requires item/NPC/state that doesn't exist
- Physics violation (flying without magic, lifting castle, etc.)
- Game-breaking exploit/loophole (duplication, reality warping)
- Blocked by world state (locked door without key, too heavy to lift)
- Prerequisite not met (can't regurgitate what wasn't swallowed)

STATE UPDATE TYPES AND REQUIRED PARAMS:
- "move_player": {{"destination": "location_id"}} - Move player to connected location
  ⚠️  BEFORE ALLOWING MOVEMENT - CHECK THE EXITS LIST AT TOP OF PROMPT:
  * ONLY allow movement in directions shown in "EXITS FROM CURRENT LOCATION"
  * If direction NOT in exits list → MUST set is_valid=false
  * Example: Exits = {{"south": "hall"}} and player says "go north" → is_valid=false
  * Example: Exits = {{"north": "chamber", "south": "entrance"}} and player says "go north" → is_valid=true, destination="chamber"
  * Set is_valid: false for ANY direction not in the exits list
  * Use no_change state update when is_valid=false
  * Narrative should explain WHY blocked (thick stone wall, no path, cliff edge, etc.)
  * DO NOT describe movement as succeeding when is_valid=false
  * Example: Player goes south (no south exit) → is_valid=false, "Thick foliage blocks your path south."
  * DO NOT say: "You move south into the clearing" (implies success)
- "add_to_inventory": {{"item_id": "item_id"}} - Pick up item from location
- "remove_from_inventory": {{"item_id": "item_id"}} - Drop item at current location (item stays in game on ground)
  * ⚠️  ONLY for dropping/placing items - item will appear at player's current location
  * ❌ DO NOT use for eating, drinking, swallowing, destroying - use consume_item instead!
- "consume_item": {{"item_id": "item_id"}} - Eat/drink/swallow/destroy item (removes from game entirely)
  * ✅ Use for: eating food, drinking potions, swallowing objects, burning items, dissolving items
  * Item is PERMANENTLY removed from game (not placed on ground)
  * 💡 TIP: For recoverable consumption (swallowing vs eating), track state in player attributes for future validation
  * See "BE A REALISTIC DM" examples above for validation patterns
- "create_item": {{"item_id": "unique_id", "name": "Item Name", "attributes": {{}}, "location": "location_id or null"}} - Dynamically create a new item
  * ⚠️  IMPORTANT: Use create_item for INANIMATE objects only (swords, potions, furniture, rocks)
  * ❌ DO NOT use for living creatures (animals, people, monsters) - use create_npc instead!
  * Use when player action naturally creates a new item (breaking antlers off, splitting item, crafting, etc.)
  * item_id must be unique (e.g., "severed_antlers", "broken_branch_1")
  * attributes can include: {{"type": "weapon/consumable/misc", "damage": "1d4", "sharp": true, etc.}}
  * location: null means add to player inventory, otherwise use location_id for ground
  * Example: Player knocks antlers off deer -> create_item with item_id="severed_antlers", location="current_location"
- "destroy_item": {{"item_id": "item_id"}} - Permanently remove item from game (different from consume_item)
- "create_location": {{"location_id": "unique_id", "name": "Location Name", "attributes": {{}}, "connections": {{}}, "from_location": "current_location_id", "direction": "south", "reverse_direction": "north"}} - Dynamically create a new location
  * Use for wishes, magical effects, or world-building actions (genie creates path, earthquake reveals cave, etc.)
  * location_id must be unique (e.g., "hidden_grove", "secret_passage_1")
  * name: Display name for the location (e.g., "Hidden Grove", "Secret Passage")
  * attributes: {{"description_hints": "lush vegetation, sparkling stream", "lighting": "bright", "is_outdoors": true, etc.}}
  * connections: Optional dict of exits from NEW location {{"north": "forest_clearing", "east": "meadow"}}
  * from_location: Location to connect FROM (usually current location or location_id)
  * direction: Direction from from_location to new location (e.g., "south", "down", "through_portal")
  * reverse_direction: Optional direction back (e.g., if direction is "south", reverse is "north")
  * Example: Genie wish for path south → create_location with from_location="forest_clearing", direction="south", reverse_direction="north"
  * ⚠️  IMPORTANT: This enables true dynamic world building - use creatively for magical effects, wishes, discoveries
- "create_npc": {{"npc_id": "unique_id", "name": "NPC Name", "attributes": {{"is_pet": true, "is_vehicle": true}}, "location": null}} - Dynamically create a new NPC (living creature)
  * ✅ Use for ALL living creatures: animals, people, monsters, companions, mounts
  * ❌ DO NOT use create_item for living things - ONLY use create_npc!
  * REQUIRED FIELDS IN PARAMS:
    - npc_id: unique ID string (e.g., "magical_horse", "guard_captain")
    - name: display name string (e.g., "Magical Horse", "Guard Captain")
    - attributes: dict with creature attributes (see below)
    - location: null (current location) or location_id string
  * 🐴 PET MECHANICS - NPCs that follow the player:
    - Set "is_pet": true in attributes to make NPC follow player when they move locations
    - Pets automatically move with player (no need for explicit move_npc)
    - Example: Horse, dog, familiar, tamed wolf
  * 🚗 VEHICLE MECHANICS - NPCs that can be ridden/driven:
    - Set "is_vehicle": true in attributes to allow player to ride/mount this NPC
    - Set "vehicle_speed": number (1=normal, 2=fast, 3=very fast) for future fast travel
    - Example: Horse (is_pet + is_vehicle), wagon, boat
  * 🎯 TAMING: Any non-pet NPC can become a pet at DM discretion
    - If player successfully tames/befriends NPC, use modify_attribute to set "is_pet": true
  * COMPLETE EXAMPLE for horse wish:
    {{"type": "create_npc", "params": {{"npc_id": "magical_horse", "name": "Magnificent Horse", "attributes": {{"creature_type": "beast", "is_pet": true, "is_vehicle": true, "vehicle_speed": 2, "hp": 30, "hp_max": 30, "hostility": "passive"}}, "location": null}}}}
- "move_item": {{"item_id": "id", "to_location": "location_id"}} - MUST include both!
- "move_npc": {{"npc_id": "id", "to_location": "location_id"}} - Move NPC to different location
- "remove_npc": {{"npc_id": "id"}} - Remove NPC from current location (teleport, banish, etc.)
- "modify_attribute": {{"entity_id": "id", "attribute_path": "path.to.attr", "value": "new_value"}}
- "set_flag": {{"flag_name": "name", "value": true}}
- "trigger_combat": {{"target_npc_id": "id", "attack_type": "melee"}}
- "update_dm_state": {{"path": "dot.separated.path", "value": any}} - Update hidden DM state for plot tracking
- "no_change": {{}} (for actions that are just narrative)

EXAMPLES OF CORRECT STATE UPDATE + NARRATIVE MATCHING:

Input: "go north" (or "n") - when at entrance and north leads to hall
{{
  "intent": "Player wants to move north",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "move_player",
      "target": null,
      "params": {{"destination": "hall"}}
    }}
  ],
  "narrative_response": "You head north into the grand hall. The vaulted ceiling looms above you, and crumbling pillars cast long shadows across the dusty floor.",
  "requires_dice_roll": false
}}

Input: "pick up the rusty sword"
{{
  "intent": "Player wants to pick up the sword",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "add_to_inventory",
      "target": "rusty_sword",
      "params": {{"item_id": "rusty_sword"}}
    }}
  ],
  "narrative_response": "You reach down and grasp the rusty sword by its worn leather grip. The blade is pitted with age but still feels sturdy in your hand. You slide it into your belt.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "throw the sword at the wall" (when sword IS in inventory)
{{
  "intent": "Player wants to throw the sword",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "remove_from_inventory",
      "target": null,
      "params": {{"item_id": "rusty_sword"}}
    }},
    {{
      "type": "modify_attribute",
      "target": "rusty_sword",
      "params": {{"attribute_path": "state.thrown", "value": true}}
    }}
  ],
  "narrative_response": "You hurl the rusty sword against the cavern wall. It clangs loudly, sending sparks and chips of stone flying. The sword clatters to the ground near the wall.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "examine the sword" (when sword is at location, NOT in inventory)
{{
  "intent": "Player wants to examine the sword",
  "is_valid": true,
  "state_updates": [],
  "narrative_response": "You crouch down to examine the rusty sword lying on the ground. The metal is pitted and worn, but you can still make out faint craftsman markings on the blade.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "eat the berries" (when berries are at location)
{{
  "intent": "Player wants to eat the wild berries",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "consume_item",
      "target": "wild_berries",
      "params": {{"item_id": "wild_berries"}}
    }}
  ],
  "narrative_response": "You gather the wild berries and eat them. A burst of sweet and slightly tart flavor fills your mouth, and you feel a bit of your strength returning. The berries are gone.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "drink the potion"
{{
  "intent": "Player wants to drink the health potion",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "consume_item",
      "target": "health_potion",
      "params": {{"item_id": "health_potion"}}
    }}
  ],
  "narrative_response": "You uncork the health potion and drink it down. The glowing red liquid tastes of mint and herbs, and you feel warmth spreading through your body as your wounds begin to heal. The empty vial slips from your fingers.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "greet the skeletal guard"
{{
  "intent": "Player wants to greet the NPC",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "modify_attribute",
      "target": "guard_skeleton",
      "params": {{"attribute_path": "state.has_been_greeted", "value": true}}
    }}
  ],
  "narrative_response": "You call out a greeting to the skeletal guard. Its hollow eye sockets turn toward you with an eerie green glow. The undead creature remains silent, but you sense a shift in its awareness.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "a wormhole opens and swallows the guard" (creative NPC removal)
{{
  "intent": "Player wants to use a wormhole to remove the skeletal guard from this location",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "remove_npc",
      "target": "skeleton_guard",
      "params": {{"npc_id": "skeleton_guard"}}
    }}
  ],
  "narrative_response": "Suddenly, a swirling vortex of energy rips open in the air before the skeletal guard. The creature emits a silent, bone-chilling shriek as it's pulled into the wormhole, vanishing without a trace. The wormhole collapses, leaving only the echo of its otherworldly energy in the hall.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "charge at the deer" (passive creature - should flee, NOT fight)
{{
  "intent": "Player charges at the passive deer, which will flee",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "remove_npc",
      "target": "deer",
      "params": {{"npc_id": "deer"}}
    }}
  ],
  "narrative_response": "You charge forward with aggressive intent. The white deer's eyes widen in alarm, and with a graceful leap, it bounds away into the forest, disappearing among the trees. The peaceful creature wanted nothing to do with violence.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Input: "I charm the rat to follow me north"
{{
  "intent": "Player wants to charm the rat and have it move to a different location",
  "is_valid": true,
  "state_updates": [
    {{
      "type": "move_npc",
      "target": "rat",
      "params": {{"npc_id": "rat", "to_location": "hall"}}
    }},
    {{
      "type": "modify_attribute",
      "target": "rat",
      "params": {{"attribute_path": "attributes.charmed", "value": true}}
    }}
  ],
  "narrative_response": "You speak soothing words to the giant rat, and its beady red eyes soften. The creature seems entranced by your voice and begins to follow you as you head north into the grand hall.",
  "requires_dice_roll": false,
  "dice_check": null
}}

Now interpret the player's action: "{player_input}"
"""

        return prompt
