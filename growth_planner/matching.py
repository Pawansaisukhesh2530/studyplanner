"""Give each club a simple, explainable match score."""


def split_tags(text):
    """Turn 'coding|technology' into {'coding', 'technology'}."""
    tags = set()
    for part in text.split("|"):
        if part.strip():
            tags.add(part.strip().lower())
    return tags


def recommend_clubs(clubs, interests, goals, hours_available):
    selected_interests = set(interests)
    selected_goals = set(goals)
    results = []

    for club in clubs:
        club_interests = split_tags(club["interests"])
        club_goals = split_tags(club["goals"])
        shared_interests = sorted(selected_interests & club_interests)
        shared_goals = sorted(selected_goals & club_goals)

        score = 3 * len(shared_interests) + 2 * len(shared_goals)
        fits_time = float(club["hours_per_week"]) <= hours_available
        if fits_time:
            score += 2

        reasons = []
        if shared_interests:
            reasons.append("Shared interests: " + ", ".join(shared_interests))
        if shared_goals:
            reasons.append("Supports goals: " + ", ".join(shared_goals))
        if fits_time:
            reasons.append("Fits your weekly time")
        else:
            reasons.append("Needs more time than you selected")

        results.append({"club": club, "score": score, "reasons": reasons})

    # Higher scores appear first. Names break ties consistently.
    results.sort(key=lambda item: (-item["score"], item["club"]["name"]))
    return results

