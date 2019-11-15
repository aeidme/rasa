
from typing import List, Optional, Dict, Text

from rasa.core.actions.action import ACTION_LISTEN_NAME
from rasa.core.domain import PREV_PREFIX
from rasa.core.events import Event
from rasa.nlu.constants import MESSAGE_INTENT_ATTRIBUTE
from rasa.core.training.generator import TrackerWithCachedStates


class StoryConflict:

    def __init__(
            self,
            sliced_states: List[Optional[Dict[Text, float]]],
            tracker: TrackerWithCachedStates,
            event
    ):
        self.sliced_states = sliced_states
        self.hash = hash(str(list(sliced_states)))
        self.tracker = tracker,
        self.event = event
        self._conflicting_actions = {}  # {"action": ["story_1", ...], ...}
        self.correct_response = None

    def events_prior_to_conflict(self):
        raise NotImplementedError

    @staticmethod
    def _get_prev_event(state) -> [Event, None]:
        if not state:
            return None
        result = None
        for k in state:
            if k.startswith(PREV_PREFIX):
                if k[len(PREV_PREFIX):] != ACTION_LISTEN_NAME:
                    result = ("action", k[len(PREV_PREFIX):])
            elif k.startswith(MESSAGE_INTENT_ATTRIBUTE + "_") and not result:
                result = ("intent", k[len(MESSAGE_INTENT_ATTRIBUTE + '_'):])
        return result

    def add_conflicting_action(self, action: Text, story_name: Text):
        if action not in self._conflicting_actions:
            self._conflicting_actions[action] = [story_name]
        else:
            self._conflicting_actions[action] += [story_name]

    @property
    def conflicting_actions(self):
        return list(self._conflicting_actions.keys())

    @property
    def conflicting_actions_with_counts(self):
        return [f"{a} [{len(s)}x]" for (a, s) in self._conflicting_actions.items()]

    @property
    def incorrect_stories(self):
        if self.correct_response:
            incorrect_stories = []
            for stories in [s for (a, s) in self._conflicting_actions.items() if a != self.correct_response]:
                for story in stories:
                    incorrect_stories.append(story)
            return incorrect_stories
        else:
            return []

    def story_prior_to_conflict(self):
        result = ""
        for state in self.sliced_states:
            if state:
                event_type, event_name = self._get_prev_event(state)
                if event_type == "intent":
                    result += f"* {event_name}\n"
                else:
                    result += f"  - {event_name}\n"
        return result

    def __str__(self):
        last_event_type, last_event_name = self._get_prev_event(self.sliced_states[-1])
        conflict_string = f"CONFLICT after {last_event_type} '{last_event_name}':\n"
        for action, stories in self._conflicting_actions.items():
            if len(stories) == 1:
                stories = f"'{stories[0]}'"
            elif len(stories) == 2:
                stories = f"'{stories[0]}' and '{stories[1]}'"
            elif len(stories) == 3:
                stories = f"'{stories[0]}', '{stories[1]}', and '{stories[2]}'"
            elif len(stories) >= 4:
                stories = f"'{stories[0]}' and {len(stories) - 1} other trackers"
            conflict_string += f"  {action} predicted in {stories}\n"

        return conflict_string
