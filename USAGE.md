# One Page Rules — Matchmaking Bot User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Commands Overview](#commands-overview)
3. [Joining the Queue](#joining-the-queue)
4. [Challenging a Rival](#challenging-a-rival)
5. [Checking Status](#checking-status)
6. [Leaving a Queue or Match](#leaving-a-queue-or-match)
7. [Queueing for Any Opponent](#queueing-for-any-opponent)
8. [Admin Reset](#admin-reset)
9. [Automatic Monthly Reset](#automatic-monthly-reset)
10. [Frequently Asked Questions](#frequently-asked-questions)

---

## Getting Started

The **One Page Rules Matchmaking Bot** helps you find opponents for your game. You can:

- **Join a queue** with your chosen system and points value — the bot automatically matches you with a compatible opponent.
- **Challenge a specific player** directly via the `/matchmaking Rival` command.
- **Queue for anyone** with `/matchmaking_any` if you don't care about system or points.

All data persists between bot restarts, so you won't lose your place in queue if the bot restarts.

---

## Commands Overview

| Command | Description | Who Can Use |
|---------|-------------|-------------|
| `/matchmaking action:Join` | Join the queue with a system and points | Everyone |
| `/matchmaking action:Rival` | Challenge a specific player | Everyone |
| `/matchmaking action:Status` | View all active matches and queued players | Everyone |
| `/matchmaking action:Leave` | Leave the queue or a confirmed match | Everyone |
| `/matchmaking_any` | Queue for any opponent (any system, any points) | Everyone |
| `/matchmaking_reset` | Clear all queues and matches | Admins only |

---

## Joining the Queue

Use this command when you want to be **automatically matched** with an opponent who has the same system and points value.

### How to Use

1. Type `/matchmaking` in any channel where the bot is active.
2. Select **Action → Join**.
3. Choose your **System**:
   - **AOF** — Army of the Federation
   - **GDF** — Global Defense Force
4. Choose your **Points** value:
   - **1000**
   - **1500**
   - **2000**
   - **3000+**
5. Press Enter.

### What Happens Next

- **If a compatible opponent is waiting** — The bot immediately creates a match and announces it in the channel.
- **If no one is waiting** — You are added to the queue. The bot will notify you (by matching you) when someone compatible joins.

### Example

```
/matchmaking action:Join system:AOF points:1500
```

**Bot response (match found):**
> ⚔️ **MATCH FOUND!** @PlayerA vs @PlayerB!
> System: **AOF** • Points: **1500**

**Bot response (no match, queued):**
> 🕰️ @PlayerA has joined the queue with system **AOF** (1500 pts). Waiting for an opponent…

---

## Challenging a Rival

Use this command when you want to **challenge a specific player** directly, bypassing the queue.

### How to Use

1. Type `/matchmaking` in any channel.
2. Select **Action → Rival**.
3. Choose an **Opponent** (a server member).
4. Choose your **System**: AOF or GDF.
5. Choose your **Points** value: 1000, 1500, 2000, or 3000+.
6. Press Enter.

### What Happens Next

1. The challenged player receives a message in the channel with **Accept** and **Decline** buttons.
2. They also receive a **DM notification** alerting them of the challenge.
3. **If they Accept** — A match is created and announced. The challenger also gets a DM confirmation.
4. **If they Decline** — The challenge is cancelled. The challenger gets a DM notification.

> **Note:** Only the challenged player can click Accept or Decline. The buttons remain active indefinitely until used.

### Example

```
/matchmaking action:Rival opponent:@PlayerB system:GDF points:2000
```

**Bot response (challenge sent):**
> @PlayerB, you have been challenged!
> 
> ⚔️ **Rival Challenge**
> **PlayerA** challenges **PlayerB**!
> System: **GDF** • Points: **2000**
> Do you accept?
> [✅ Accept] [❌ Decline]

---

## Checking Status

Use this command to see **all current matches** and **everyone waiting in the queue**.

### How to Use

1. Type `/matchmaking` in any channel.
2. Select **Action → Status**.
3. Press Enter.

### What You'll See

The bot responds with an embed showing:

- **Active Matches** — All confirmed matches with player names, systems, and points.
- **Waiting in Queue** — All players currently waiting, with their system and points.

### Example

```
/matchmaking action:Status
```

**Bot response:**

> **📋 Matchmaking Status**
>
> **Active Matches**
> ⚔️ **PlayerA** (AOF, 1500 pts) vs **PlayerB** (AOF, 1500 pts)
> ⚔️ **PlayerC** (GDF, 2000 pts) vs **PlayerD** (GDF, 2000 pts)
>
> **Waiting in Queue**
> 🕰️ **PlayerE** (AOF, 1000 pts): WAITING OPPONENT
> 🕰️ **PlayerF** (GDF, 3000+ pts): WAITING OPPONENT

---

## Leaving a Queue or Match

Use this command to **remove yourself** from the queue or from a confirmed match.

### How to Use

1. Type `/matchmaking` in any channel.
2. Select **Action → Leave**.
3. Choose **Leave Target**:
   - **Queue** — Remove yourself from the matchmaking queue (if you're waiting).
   - **Match** — Leave a confirmed match (your opponent will be notified).
4. Press Enter.

### What Happens Next

- **Leaving the Queue** — You are silently removed. You get an ephemeral confirmation.
- **Leaving a Match** — Your opponent is **pinged** and notified that you left. They may need to find a new opponent.

### Example

```
/matchmaking action:Leave leave_target:Queue
```

**Bot response (queue):**
> 👋 You have been removed from the matchmaking queue.

```
/matchmaking action:Leave leave_target:Match
```

**Bot response (match):**
> @PlayerB — **PlayerB**, your opponent has left the match.
> 👋 @PlayerA has been removed from their confirmed match.

---

## Queueing for Any Opponent

Use `/matchmaking_any` when you want to **play regardless of system or points**. This is the fastest way to get a match.

### How to Use

1. Type `/matchmaking_any` in any channel.
2. Press Enter.

### What Happens Next

- **If someone is already in the queue** — You are immediately matched with them. You adopt **their** system and points settings.
- **If no one is waiting** — You are added to the queue as **ANY**. The next person who uses `/matchmaking_any` will be matched with you.

### Example

```
/matchmaking_any
```

**Bot response (match found):**
> ⚔️ **MATCH FOUND!** @PlayerA vs @Player B!
> System: **AOF** • Points: **1500**
> *(matched using their settings via **Any**)*

**Bot response (no match, queued):**
> 🕰️ @PlayerA has joined the queue as **ANY** (any system, any points). Waiting for an opponent…

---

## Admin Reset

Server administrators can manually **clear all queues and matches** at any time.

### How to Use

1. Type `/matchmaking_reset` in any channel.
2. Press Enter.

> **Requires:** Administrator permission on the server.

### What Happens Next

- All queued players are removed.
- All active matches are cleared.
- A confirmation message is posted in the channel.

### Example

```
/matchmaking_reset
```

**Bot response:**
> 🧹 **MATCHMAKING RESET** — All queues and matches have been cleared.

---

## Automatic Monthly Reset

The bot **automatically resets** all matchmaking data on the **second Friday of every month**. This ensures a fresh start for competitive seasons.

- The reset happens **once per month**.
- A notification is posted in the server's system channel (if available).
- The exact date is tracked internally so the reset only fires once, even if the bot restarts.

---

## Frequently Asked Questions

### Can I be in the queue and in a match at the same time?

No. If you are already in a confirmed match, you cannot join the queue. You must leave your current match first.

### What happens if I leave a match?

Your opponent is notified via a ping in the channel. The match is removed from the active matches list.

### Can I challenge myself?

No. The bot prevents self-challenges.

### Can I challenge a bot?

No. The bot prevents challenging other bots.

### What if I miss the Accept/Decline buttons on a challenge?

The buttons **never expire**. They remain active on the message until someone clicks them. Scroll up to find the challenge message.

### Does the bot remember my queue position after a restart?

Yes. All data is saved to a JSON file and persists across restarts.

### What's the difference between `/matchmaking Join` and `/matchmaking_any`?

- `/matchmaking Join` requires you to pick a **specific system and points**. You will only be matched with someone who chose the same settings.
- `/matchmaking_any` matches you with **anyone** waiting. You inherit their system and points.

### I joined the queue but no one is matching me. What should I do?

Check `/matchmaking Status` to see if anyone else is waiting. If the queue is empty, you'll need to wait for another player to join with the same system and points — or use `/matchmaking_any` to play with whoever shows up next.

### Can I change my system or points after joining the queue?

Not directly. You need to `/matchmaking Leave` the queue first, then rejoin with new settings.
