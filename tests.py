#!/usr/bin/env python3
"""
A script for running all the designated test cases for the Mingle API

Install:
  pip install requests

Run:
  python tests.py http://<VM_IP>:<VM_PORT>
"""

import sys
import time
import requests


def post_json(url, data, headers=None):
    return requests.post(url, json=data, headers=headers)


def get(url, headers=None, params=None):
    return requests.get(url, headers=headers, params=params)


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def print_step(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def show_expected_actual(label, expected, actual):
    print(f"{label}")
    print(f"  Expected: {expected}")
    print(f"  Actual:   {actual}")


def try_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def register(base, name, email, password):
    url = f"{base}/api/auth/register"
    r = post_json(url, {"name": name, "email": email, "password": password})
    show_expected_actual(
        f"Register {name}",
        "201 Created (or 409 if already registered)",
        f"{r.status_code}",
    )
    return r


def login(base, email, password):
    url = f"{base}/api/auth/login"
    r = post_json(url, {"email": email, "password": password})
    show_expected_actual(
        f"Login {email}",
        "200 OK + token",
        f"{r.status_code}",
    )
    tok = None
    if r.status_code == 200:
        data = try_json(r)
        if data:
            tok = data.get("token")
    return tok


def create_post(base, token, title, topics, body, expires_in_minutes):
    url = f"{base}/api/posts"
    r = post_json(
        url,
        {
            "title": title,
            "topics": topics,
            "body": body,
            "expiresInMinutes": expires_in_minutes,
        },
        headers=auth_headers(token),
    )
    show_expected_actual(
        f"Create post '{title}'",
        "201 Created + post JSON",
        f"{r.status_code}",
    )
    post_id = None
    if r.status_code == 201:
        data = try_json(r)
        if data:
            post_id = data.get("_id")
    if post_id:
        print("  Post ID:", post_id)
    return post_id


def browse_topic(base, token, topic):
    url = f"{base}/api/posts"
    r = get(url, headers=auth_headers(token), params={"topic": topic})
    show_expected_actual(
        f"Browse topic={topic}",
        "200 OK + list of posts",
        f"{r.status_code}",
    )
    if r.status_code == 200:
        data = try_json(r)
        if isinstance(data, list):
            print("  Returned posts:", len(data))
            return data
    return []


def like(base, token, post_id, who=""):
    url = f"{base}/api/posts/{post_id}/like"
    r = requests.post(url, headers=auth_headers(token))
    label = f"Like post ({who})" if who else "Like post"
    show_expected_actual(
        label,
        "200 OK (or error if invalid action)",
        f"{r.status_code}",
    )
    return r


def dislike(base, token, post_id, who=""):
    url = f"{base}/api/posts/{post_id}/dislike"
    r = requests.post(url, headers=auth_headers(token))
    label = f"Dislike post ({who})" if who else "Dislike post"
    show_expected_actual(
        label,
        "200 OK (or error if invalid action)",
        f"{r.status_code}",
    )
    return r


def comment(base, token, post_id, text, who=""):
    url = f"{base}/api/posts/{post_id}/comments"
    r = post_json(url, {"text": text}, headers=auth_headers(token))
    label = f"Comment ({who})" if who else "Comment"
    show_expected_actual(
        label,
        "201 Created (or 200 OK) + comment info",
        f"{r.status_code}",
    )
    return r


def most_active(base, token, topic):
    url = f"{base}/api/topics/{topic}/most-active"
    r = get(url, headers=auth_headers(token))
    show_expected_actual(
        f"Most active topic={topic}",
        "200 OK + one post",
        f"{r.status_code}",
    )
    if r.status_code == 200:
        return try_json(r)
    return None


def expired_by_topic(base, token, topic):
    url = f"{base}/api/topics/{topic}/expired"
    r = get(url, headers=auth_headers(token))
    show_expected_actual(
        f"Expired posts topic={topic}",
        "200 OK + [] if none",
        f"{r.status_code}",
    )
    if r.status_code == 200:
        return try_json(r)
    return None


def find_post(posts, post_id):
    for p in posts:
        if p.get("_id") == post_id:
            return p
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python mingle_tests_simple.py http://<VM_IP>:3000")
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    password = "StrongPass123"

    # TC1 / TC2
    print_step("TC1/TC2: Register + Login (get tokens)")
    users = [
        ("Olga", "olga@mingle.com"),
        ("Nick", "nick@mingle.com"),
        ("Mary", "mary@mingle.com"),
        ("Nestor", "nestor@mingle.com"),
    ]

    for name, email in users:
        register(base, name, email, password)

    tokens = {}
    for name, email in users:
        tok = login(base, email, password)
        tokens[name] = tok

    if not all(tokens.values()):
        print("\nSome logins failed (token missing). Stopping early.")
        sys.exit(1)

    # TC3
    print_step("TC3: Unauthorised request (no token)")
    r = get(f"{base}/api/posts", params={"topic": "Tech"})
    show_expected_actual(
        "Browse Tech without token",
        "401 Unauthorized",
        f"{r.status_code}",
    )

    # TC4/5/6
    print_step("TC4/TC5/TC6: Create Tech posts (Olga, Nick, Mary)")
    olga_post = create_post(base, tokens["Olga"], "Olga Tech Post", ["Tech"], "Olga: Hello Tech!", 5)
    nick_post = create_post(base, tokens["Nick"], "Nick Tech Post", ["Tech"], "Nick: Tech thoughts.", 5)
    mary_post = create_post(base, tokens["Mary"], "Mary Tech Post", ["Tech"], "Mary: AI topic.", 5)

    if not (olga_post and nick_post and mary_post):
        print("\nOne or more posts failed to create. Stopping early.")
        sys.exit(1)

    # TC7
    print_step("TC7: Browse Tech posts (Nick + Olga)")
    tech_posts_nick = browse_topic(base, tokens["Nick"], "Tech")
    tech_posts_olga = browse_topic(base, tokens["Olga"], "Tech")
    print("  (Just a note) Expecting to see at least 3 posts total.")

    # TC8
    print_step("TC8: Nick and Olga like Mary's Tech post")
    show_expected_actual("Nick likes Mary", "200 OK", like(base, tokens["Nick"], mary_post, who="Nick").status_code)
    show_expected_actual("Olga likes Mary", "200 OK", like(base, tokens["Olga"], mary_post, who="Olga").status_code)

    # TC9
    print_step("TC9: Nestor likes Nick's post and dislikes Mary's post")
    show_expected_actual("Nestor likes Nick", "200 OK", like(base, tokens["Nestor"], nick_post, who="Nestor").status_code)
    show_expected_actual("Nestor dislikes Mary", "200 OK", dislike(base, tokens["Nestor"], mary_post, who="Nestor").status_code)

    # TC10
    print_step("TC10: Nick browses Tech posts (check counts)")
    tech_posts = browse_topic(base, tokens["Nick"], "Tech")
    p_mary = find_post(tech_posts, mary_post)
    p_nick = find_post(tech_posts, nick_post)

    print("\nCounts (expected vs actual):")
    if p_mary:
        show_expected_actual("Mary likes", "2", str(p_mary.get("likesCount")))
        show_expected_actual("Mary dislikes", "1", str(p_mary.get("dislikesCount")))
        show_expected_actual("Mary comments", "0", str(len(p_mary.get("comments", []))))
    else:
        print("  Couldn't find Mary's post in the list (unexpected).")

    if p_nick:
        show_expected_actual("Nick likes", "1", str(p_nick.get("likesCount")))
    else:
        print("  Couldn't find Nick's post in the list (unexpected).")

    # TC11
    print_step("TC11: Mary tries to like her own post (should fail)")
    r = like(base, tokens["Mary"], mary_post, who="Mary (self-like)")
    show_expected_actual(
        "Mary self-like",
        "403 Forbidden (or 409 Conflict depending on your API)",
        f"{r.status_code}",
    )
    if r.status_code not in (403, 409):
        data = try_json(r)
        if data:
            print("  Response:", data)

    # TC12
    print_step("TC12: Nick and Olga comment on Mary's post (2 each)")
    comment(base, tokens["Nick"], mary_post, "Nick comment #1", who="Nick")
    comment(base, tokens["Olga"], mary_post, "Olga comment #1", who="Olga")
    comment(base, tokens["Nick"], mary_post, "Nick comment #2", who="Nick")
    comment(base, tokens["Olga"], mary_post, "Olga comment #2", who="Olga")

    # TC13
    print_step("TC13: Nick browses Tech (see comments)")
    tech_posts = browse_topic(base, tokens["Nick"], "Tech")
    p_mary = find_post(tech_posts, mary_post)
    if p_mary:
        show_expected_actual("Mary comments count", "4", str(len(p_mary.get("comments", []))))
    else:
        print("  Couldn't find Mary's post to check comments.")

    # TC14
    print_step("TC14: Nestor creates Health post (1 minute expiry)")
    nestor_health = create_post(
        base,
        tokens["Nestor"],
        "Nestor Health Post",
        ["Health"],
        "Nestor: Health topic message.",
        1,
    )

    if not nestor_health:
        print("\nHealth post creation failed. Stopping early.")
        sys.exit(1)

    # TC15
    print_step("TC15: Mary browses Health posts (should see Nestor's post)")
    health_posts = browse_topic(base, tokens["Mary"], "Health")
    print("  (Just a note) Expecting at least 1 Health post.")

    # TC16
    print_step("TC16: Mary comments on Nestor's Health post")
    comment(base, tokens["Mary"], nestor_health, "Mary: commenting on Health post", who="Mary")

    # TC17
    print_step("TC17: After expiry, Mary dislikes Nestor's Health post (should fail)")
    print("Waiting ~75 seconds for expiry...")
    time.sleep(75)
    r = dislike(base, tokens["Mary"], nestor_health, who="Mary (after expiry)")
    show_expected_actual("Dislike after expiry", "403 Forbidden", f"{r.status_code}")

    # TC18
    print_step("TC18: Nestor browses Health posts (should see 1 comment)")
    health_posts = browse_topic(base, tokens["Nestor"], "Health")
    p_health = find_post(health_posts, nestor_health)
    if p_health:
        show_expected_actual("Health post comments", "1", str(len(p_health.get("comments", []))))
    else:
        print("  Couldn't find Nestor's Health post.")

    # TC19
    print_step("TC19: Nick checks expired posts in Sport (should be empty)")
    expired_sport = expired_by_topic(base, tokens["Nick"], "Sport")
    if isinstance(expired_sport, list):
        show_expected_actual("Expired Sport list length", "0", str(len(expired_sport)))
    else:
        print("  Didn't get a list back for expired Sport posts.")

    # TC20
    print_step("TC20: Nestor queries most active Tech post (should be Mary's)")
    active = most_active(base, tokens["Nestor"], "Tech")
    if active:
        show_expected_actual("Most active Tech post ID", mary_post, str(active.get("_id")))
    else:
        print("  Didn't get a response for most active Tech post.")

    print("\nDone.")


if __name__ == "__main__":
    main()
