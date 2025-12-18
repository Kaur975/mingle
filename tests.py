#!/usr/bin/env python3
"""
A script for running all the designated test cases for the Mingle API

Install:
  pip install requests

Run:
  python tests.py http://<VM_IP>:3000
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
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def register(base, name, email, password):
    url = f"{base}/api/auth/register"
    r = post_json(url, {"name": name, "email": email, "password": password})
    print(f"Register {name}: {r.status_code}")
    # 201 (created) or 409 (already exists) is fine for reruns
    return r


def login(base, email, password):
    url = f"{base}/api/auth/login"
    r = post_json(url, {"email": email, "password": password})
    print(f"Login {email}: {r.status_code}")
    if r.status_code == 200:
        return r.json().get("token")
    return None


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
    print(f"Create post '{title}': {r.status_code}")
    if r.status_code == 201:
        return r.json().get("_id")
    return None


def browse_topic(base, token, topic):
    url = f"{base}/api/posts"
    r = get(url, headers=auth_headers(token), params={"topic": topic})
    print(f"Browse topic={topic}: {r.status_code}")
    if r.status_code == 200:
        return r.json()
    return []


def like(base, token, post_id):
    url = f"{base}/api/posts/{post_id}/like"
    r = requests.post(url, headers=auth_headers(token))
    print(f"Like {post_id}: {r.status_code}")
    return r


def dislike(base, token, post_id):
    url = f"{base}/api/posts/{post_id}/dislike"
    r = requests.post(url, headers=auth_headers(token))
    print(f"Dislike {post_id}: {r.status_code}")
    return r


def comment(base, token, post_id, text):
    url = f"{base}/api/posts/{post_id}/comments"
    r = post_json(url, {"text": text}, headers=auth_headers(token))
    print(f"Comment {post_id}: {r.status_code}")
    return r


def most_active(base, token, topic):
    url = f"{base}/api/topics/{topic}/most-active"
    r = get(url, headers=auth_headers(token))
    print(f"Most active {topic}: {r.status_code}")
    if r.status_code == 200:
        return r.json()
    return None


def expired_by_topic(base, token, topic):
    url = f"{base}/api/topics/{topic}/expired"
    r = get(url, headers=auth_headers(token))
    print(f"Expired posts {topic}: {r.status_code}")
    if r.status_code == 200:
        return r.json()
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

    # TC1 / TC2: Register + Login
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
        print("Some logins failed, cannot continue.")
        sys.exit(1)

    # TC3: Call without token should fail
    print_step("TC3: Unauthorised request (no token)")
    r = get(f"{base}/api/posts", params={"topic": "Tech"})
    print("Browse Tech without token:", r.status_code, "(expected 401)")

    # TC4/5/6: Create three Tech posts
    print_step("TC4/TC5/TC6: Create Tech posts (Olga, Nick, Mary)")
    olga_post = create_post(base, tokens["Olga"], "Olga Tech Post", ["Tech"], "Olga: Hello Tech!", 5)
    nick_post = create_post(base, tokens["Nick"], "Nick Tech Post", ["Tech"], "Nick: Tech thoughts.", 5)
    mary_post = create_post(base, tokens["Mary"], "Mary Tech Post", ["Tech"], "Mary: AI topic.", 5)

    if not (olga_post and nick_post and mary_post):
        print("Post creation failed, cannot continue.")
        sys.exit(1)

    # TC7: Browse Tech (expect at least those 3)
    print_step("TC7: Browse Tech posts (Nick + Olga)")
    tech_posts_nick = browse_topic(base, tokens["Nick"], "Tech")
    tech_posts_olga = browse_topic(base, tokens["Olga"], "Tech")

    print("Tech posts found (Nick):", len(tech_posts_nick))
    print("Tech posts found (Olga):", len(tech_posts_olga))

    # TC8: Nick + Olga like Mary's post
    print_step("TC8: Nick and Olga like Mary's Tech post")
    like(base, tokens["Nick"], mary_post)
    like(base, tokens["Olga"], mary_post)

    # TC9: Nestor likes Nick, dislikes Mary
    print_step("TC9: Nestor likes Nick's post and dislikes Mary's post")
    like(base, tokens["Nestor"], nick_post)
    dislike(base, tokens["Nestor"], mary_post)

    # TC10: Nick browses Tech, check counts (light check)
    print_step("TC10: Nick browses Tech posts (check counts)")
    tech_posts = browse_topic(base, tokens["Nick"], "Tech")
    p_mary = find_post(tech_posts, mary_post)
    p_nick = find_post(tech_posts, nick_post)

    if p_mary:
        print("Mary counts:", "likes=", p_mary.get("likesCount"), "dislikes=", p_mary.get("dislikesCount"))
    if p_nick:
        print("Nick counts:", "likes=", p_nick.get("likesCount"), "dislikes=", p_nick.get("dislikesCount"))

    # TC11: Mary likes her own post (should fail)
    print_step("TC11: Mary tries to like her own post (should fail)")
    r = like(base, tokens["Mary"], mary_post)
    print("Mary self-like response:", r.status_code, "(expected 403/409)")

    # TC12: Comments on Mary's post
    print_step("TC12: Nick and Olga comment on Mary's post (2 each)")
    comment(base, tokens["Nick"], mary_post, "Nick comment #1")
    comment(base, tokens["Olga"], mary_post, "Olga comment #1")
    comment(base, tokens["Nick"], mary_post, "Nick comment #2")
    comment(base, tokens["Olga"], mary_post, "Olga comment #2")

    # TC13: Browse Tech again and print comment count
    print_step("TC13: Nick browses Tech (see comments)")
    tech_posts = browse_topic(base, tokens["Nick"], "Tech")
    p_mary = find_post(tech_posts, mary_post)
    if p_mary:
        print("Mary comments:", len(p_mary.get("comments", [])))

    # TC14: Nestor creates Health post (short expiry)
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
        print("Health post creation failed.")
        sys.exit(1)

    # TC15: Mary browses Health
    print_step("TC15: Mary browses Health posts")
    health_posts = browse_topic(base, tokens["Mary"], "Health")
    print("Health posts found:", len(health_posts))

    # TC16: Mary comments on Nestor's Health post
    print_step("TC16: Mary comments on Nestor's Health post")
    comment(base, tokens["Mary"], nestor_health, "Mary: commenting on Health post")

    # TC17: Wait for expiry then dislike should fail
    print_step("TC17: After expiry, Mary dislikes Nestor's Health post (should fail)")
    print("Waiting ~75 seconds for expiry...")
    time.sleep(75)
    r = dislike(base, tokens["Mary"], nestor_health)
    print("Dislike after expiry:", r.status_code, "(expected 403)")

    # TC18: Nestor browses Health and prints comment count
    print_step("TC18: Nestor browses Health posts (should see 1 comment)")
    health_posts = browse_topic(base, tokens["Nestor"], "Health")
    p_health = find_post(health_posts, nestor_health)
    if p_health:
        print("Nestor health comments:", len(p_health.get("comments", [])))

    # TC19: Nick browses expired Sport posts (should be empty)
    print_step("TC19: Nick checks expired posts in Sport (should be empty)")
    expired_sport = expired_by_topic(base, tokens["Nick"], "Sport")
    if isinstance(expired_sport, list):
        print("Expired Sport count:", len(expired_sport))

    # TC20: Most active Tech should be Mary's post
    print_step("TC20: Nestor queries most active Tech post (should be Mary's)")
    active = most_active(base, tokens["Nestor"], "Tech")
    if active:
        print("Most active Tech post id:", active.get("_id"))
        print("Expected Mary post id:", mary_post)

    print("\nDone.")


if __name__ == "__main__":
    main()
