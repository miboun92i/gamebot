TASK_POOL = {
    "messages_10": {"label":"Envoie 10 messages", "target":10, "reward":25, "event":"message"},
    "messages_25": {"label":"Envoie 25 messages", "target":25, "reward":50, "event":"message"},
    "photo_1": {"label":"Envoie 1 photo", "target":1, "reward":25, "event":"photo"},
    "video_1": {"label":"Envoie 1 vidéo", "target":1, "reward":25, "event":"video"},
    "voice_1": {"label":"Envoie 1 vocal", "target":1, "reward":25, "event":"voice"},
    "media_3": {"label":"Envoie 3 médias", "target":3, "reward":50, "event":"media"},
    "voice_3": {"label":"Envoie 3 vocaux", "target":3, "reward":50, "event":"voice"},
    "replies_3": {"label":"Réponds à 3 messages", "target":3, "reward":25, "event":"reply"},
    "replies_5": {"label":"Réponds à 5 messages", "target":5, "reward":50, "event":"reply"},
    "reply_people_3": {"label":"Réponds à 3 membres différents", "target":3, "reward":50, "event":"reply_unique"},
    "interact_3": {"label":"Échange avec 3 membres différents", "target":3, "reward":50, "event":"reply_unique"},
    "react_3": {"label":"Réagis aux messages de 3 membres différents", "target":3, "reward":50, "event":"reaction_given_unique"},
    "react_5": {"label":"Réagis à 5 messages différents", "target":5, "reward":50, "event":"reaction_given"},
    "received_5_one": {"label":"Obtiens 5 réactions sur un message", "target":5, "reward":50, "event":"reaction_one"},
    "received_8_one": {"label":"Obtiens 8 réactions sur un message", "target":8, "reward":75, "event":"reaction_one"},
    "received_15": {"label":"Obtiens 15 réactions cumulées", "target":15, "reward":75, "event":"reaction_received"},
    "answers_3_one": {"label":"Obtiens 3 réponses sur un message", "target":3, "reward":50, "event":"answer_one"},
    "answers_5_one": {"label":"Obtiens 5 réponses sur un message", "target":5, "reward":75, "event":"answer_one"},
    "answers_5": {"label":"Obtiens 5 réponses cumulées", "target":5, "reward":50, "event":"answer_received"},
    "media_mix_3": {"label":"Envoie 3 médias dans la journée", "target":3, "reward":50, "event":"media"},
}
DAILY_TASK_COUNT=5
DAILY_BONUS=100
