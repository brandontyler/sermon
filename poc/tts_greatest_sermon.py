#!/usr/bin/env python3
"""Generate TTS audio for the 'greatest sermon' with SSML style shifts for emotional range."""

import os
import sys
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_PATH = SCRIPT_DIR / "samples" / "greatest_sermon_romans8.wav"

REGION = "eastus2"
TTS_ENDPOINT = f"https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
SPEECH_KEY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SPEECH_KEY", "")
VOICE = "en-US-DavisNeural"  # Has chat, cheerful, excited, hopeful, sad styles

# Sermon broken into emotional sections with SSML style tags
# This gives Parselmouth real pitch/intensity variation to detect
SSML = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'
       xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
<voice name='{VOICE}'>

<mstts:express-as style="friendly" styledegree="0.8">
<prosody rate="-5%" pitch="+2%">
Open your Bibles with me to Romans chapter 8, verses 28 through 30.

If you've been a Christian for any length of time, you've probably heard Romans 8:28 quoted more than almost any other verse. It shows up on greeting cards, on coffee mugs, in hospital waiting rooms. "And we know that in all things God works for the good of those who love him, who have been called according to his purpose."
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="excited" styledegree="0.7">
<prosody rate="+5%" pitch="+5%">
But here's what I want us to see this morning — that verse is not a greeting card. It is one of the most theologically dense, pastorally explosive statements in all of Scripture. And if we rip it out of its context, we don't just misunderstand it — we actually lose the very comfort it was designed to give.
</prosody>
</mstts:express-as>

<break time="600ms"/>

<mstts:express-as style="friendly">
<prosody rate="-8%">
So let's read it together. Romans 8, beginning in verse 28:

"And we know that in all things God works for the good of those who love him, who have been called according to his purpose. <break time="400ms"/> For those God foreknew he also predestined to be conformed to the image of his Son, that he might be the firstborn among many brothers and sisters. <break time="400ms"/> And those he predestined, he also called; those he called, he also justified; those he justified, he also glorified."

<break time="1000ms"/>

Three verses. And in those three verses, Paul gives us the entire arc of salvation — from eternity past to eternity future — in a single breath.
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="chat">
<prosody rate="-3%">
Let's take this apart carefully.

First, look at the word "know" in verse 28. "We know." Paul doesn't say "we hope." He doesn't say "we feel." He says we know. The Greek word here is "oidamen" — it carries the sense of settled, confident knowledge. Not wishful thinking. Not optimism. This is a conviction rooted in the character of God himself.
</prosody>
</mstts:express-as>

<break time="600ms"/>

<mstts:express-as style="sad" styledegree="0.6">
<prosody rate="-10%" pitch="-3%">
And what do we know? That "in all things God works for the good." Now, stop right there. Notice what Paul does not say. He does not say "all things are good." Cancer is not good. <break time="500ms"/> Betrayal is not good. <break time="500ms"/> The death of a child is not good. <break time="500ms"/> Paul is not asking you to paste a smiley face on your suffering.
</prosody>
</mstts:express-as>

<mstts:express-as style="hopeful" styledegree="0.9">
<prosody rate="-5%">
He is saying something far more profound — that God is at work in all things, including the darkest things, weaving them toward an outcome that is genuinely, eternally good.
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="chat">
<prosody rate="-5%">
The early church father Augustine wrestled with this deeply. In his Confessions, written in 397 AD, he reflected on the years he spent running from God — the wasted time, the broken relationships, the philosophical dead ends. And yet looking back, he could see how God had been working even through his rebellion to bring him to faith. Augustine wrote, "You were within me, but I was outside myself." That is Romans 8:28 lived out — not that the suffering was good, but that God was working through it.
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="excited" styledegree="0.6">
<prosody rate="+3%">
But we need to ask the critical question: good for whom? And good in what sense? This is where most people get Romans 8:28 wrong. They read "good" and they think comfort, health, financial security, a parking spot at the mall.
</prosody>
</mstts:express-as>

<break time="400ms"/>

<mstts:express-as style="friendly" styledegree="0.9">
<prosody rate="-5%">
But look at verse 29. Paul defines the "good" for us. He doesn't leave it ambiguous.

Verse 29: "For those God foreknew he also predestined to be conformed to the image of his Son."

<break time="800ms"/>

There it is. The "good" that God is working all things toward is not your comfort. It is your conformity to Christ. God's goal for your life is not that you would be happy in the shallow sense. It is that you would look like Jesus.
</prosody>
</mstts:express-as>

<break time="600ms"/>

<mstts:express-as style="chat">
<prosody rate="-3%">
The Greek word for "conformed" here is "summorphous." It comes from "sun" — together with — and "morphe" — the essential form or nature. This is not external imitation. This is deep, structural transformation. God is not putting a Jesus costume on you. He is remaking you from the inside out into the likeness of his Son.
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="excited" styledegree="0.8">
<prosody rate="+5%" pitch="+3%">
And notice the logic of Paul's argument. He says God "foreknew" — then "predestined" — then "called" — then "justified" — then "glorified." Theologians call this the golden chain of salvation. Five links. And not one of them depends on you.
</prosody>
</mstts:express-as>

<break time="1000ms"/>

<mstts:express-as style="excited" styledegree="1.2">
<prosody rate="-5%" pitch="+5%">
Let me say that again, because this is where the comfort actually lives. <break time="600ms"/> Not one link in this chain depends on you.

<break time="400ms"/>

God foreknew. <break time="300ms"/> God predestined. <break time="300ms"/> God called. <break time="300ms"/> God justified. <break time="300ms"/> God glorified. <break time="500ms"/> The subject of every single verb is God. You are the object. You are the one being acted upon.
</prosody>
</mstts:express-as>

<mstts:express-as style="hopeful" styledegree="1.0">
<prosody rate="-8%">
And that is the most comforting truth in the universe — because if your salvation depended on you, you would have reason to worry. But it doesn't depend on you. It depends on him. <break time="500ms"/> And he does not fail.
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="chat">
<prosody rate="-3%">
Now, some of you are uncomfortable with the word "predestined." I understand that. The Reformers debated this intensely. John Calvin emphasized God's sovereign election. John Wesley emphasized God's prevenient grace that enables human response. Faithful Christians have landed in different places on this for centuries. But here is what both sides agree on — the initiative belongs to God. Whether you emphasize divine sovereignty or human response, Romans 8:29 is clear: God is the one who set this plan in motion before you were born, before the foundation of the world.
</prosody>
</mstts:express-as>

<break time="600ms"/>

<mstts:express-as style="excited" styledegree="0.9">
<prosody rate="+3%" pitch="+4%">
And look at the end of the chain in verse 30. Paul says "those he justified, he also glorified." Past tense. <break time="400ms"/> Glorified. Not "will glorify." Not "hopes to glorify." <break time="300ms"/> Glorified. As if it's already done.
</prosody>
</mstts:express-as>

<break time="600ms"/>

<mstts:express-as style="sad" styledegree="0.5">
<prosody rate="-8%" pitch="-2%">
You're sitting here in 2026, struggling with sin, battling anxiety, wondering if God has forgotten you —
</prosody>
</mstts:express-as>

<mstts:express-as style="hopeful" styledegree="1.0">
<prosody rate="-5%" pitch="+3%">
and Paul writes about your glorification in the past tense. Why? Because from God's perspective, it is as good as done. The same God who called you and justified you will glorify you. And if he has already done the hardest part — sending his Son to die for you while you were still his enemy, as Paul said back in Romans 5:8 — then the glorification is the easy part. It's the inevitable conclusion of what he already started.
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="chat">
<prosody rate="-5%">
The 16th century Reformer Martin Luther called this the "wonderful exchange" — Christ takes our sin, and we receive his righteousness. And Romans 8:30 tells us that exchange doesn't stop at justification. It carries all the way through to glorification. What God starts, God finishes.
</prosody>
</mstts:express-as>

<break time="1000ms"/>

<mstts:express-as style="sad" styledegree="0.7">
<prosody rate="-10%" pitch="-3%">
So what does this mean for you on a Tuesday morning when the diagnosis comes back bad? <break time="500ms"/> What does it mean on a Friday night when your marriage is falling apart? <break time="500ms"/> What does it mean when you've lost your job and you're staring at the ceiling at 3 AM?
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="hopeful" styledegree="1.2">
<prosody rate="-5%" pitch="+2%">
It means this: the God who knew you before time, who chose you, who called you out of darkness, who declared you righteous through the blood of his Son — that God is not done with you. He is working. Right now. In this. Not around your pain, but through it. Conforming you to the image of Christ.
</prosody>
</mstts:express-as>

<break time="1000ms"/>

<mstts:express-as style="friendly" styledegree="0.9">
<prosody rate="-3%">
Here is what I want you to do this week. I want you to pick the one thing in your life right now that feels most broken — the relationship, the health struggle, the financial pressure, the grief you can't shake. And I want you to pray this prayer every morning: "God, I don't see how this is good. But I trust that you are working in this to make me more like Jesus. Show me what you're doing."

<break time="600ms"/>

Not "make this go away." Not "fix this on my timeline." But "show me what you're doing." That is a Romans 8:28 prayer. It doesn't deny the pain. It trusts the purpose.

<break time="600ms"/>

And then I want you to find one person this week — a friend, a spouse, a small group member — and tell them what you're praying. Don't carry this alone. The "those" in verse 30 is plural. God is not conforming you to Christ in isolation. He is doing it in community, through the body of Christ, as we bear one another's burdens.
</prosody>
</mstts:express-as>

<break time="800ms"/>

<mstts:express-as style="hopeful" styledegree="0.8">
<prosody rate="-8%">
Dietrich Bonhoeffer, the German pastor who was executed by the Nazis in 1945, wrote from his prison cell: "I believe that God can and will bring good out of evil, even out of the greatest evil. For that purpose he needs men who make the best use of everything." Bonhoeffer was living Romans 8:28 in a concentration camp. Not with naive optimism, but with a deep, settled confidence that God's purposes cannot be thwarted.
</prosody>
</mstts:express-as>

<break time="1000ms"/>

<mstts:express-as style="excited" styledegree="1.0">
<prosody rate="-5%" pitch="+4%">
Church, that is the promise of this text. Not that life will be easy. Not that you will understand every chapter of your story while you're living it. But that the Author of your story is good, and he is sovereign, and he finishes what he starts.

<break time="600ms"/>

From foreknowledge to glorification — every link in the chain holds. Because every link is forged by God himself.
</prosody>
</mstts:express-as>

<break time="1200ms"/>

<mstts:express-as style="hopeful" styledegree="0.6">
<prosody rate="-12%" pitch="-2%">
Let's pray.

Father, we confess that we often reduce Romans 8:28 to a bumper sticker when it is meant to be an anchor. <break time="400ms"/> Forgive us for wanting comfort without conformity. <break time="400ms"/> Teach us to trust your purposes even when we cannot see your hand. <break time="600ms"/> We thank you that our salvation does not depend on our grip on you, but on your grip on us. <break time="400ms"/> And we rest today in the unbreakable chain of your grace — foreknown, predestined, called, justified, glorified. All by you. All for your glory. <break time="600ms"/> In the name of Jesus Christ, who is the firstborn among many brothers and sisters. <break time="400ms"/> Amen.
</prosody>
</mstts:express-as>

</voice>
</speak>"""

if not SPEECH_KEY:
    print("Usage: python3 tts_greatest_sermon.py <SPEECH_KEY>")
    sys.exit(1)

headers = {
    "Ocp-Apim-Subscription-Key": SPEECH_KEY,
    "Content-Type": "application/ssml+xml",
    "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
    "User-Agent": "PSR-POC",
}

print(f"Voice: {VOICE}")
print(f"SSML length: {len(SSML)} chars")
print("Synthesizing... (may take 30-60s)")

resp = requests.post(TTS_ENDPOINT, headers=headers, data=SSML.encode("utf-8"))

if resp.status_code != 200:
    print(f"ERROR {resp.status_code}: {resp.text[:500]}")
    sys.exit(1)

OUTPUT_PATH.write_bytes(resp.content)
size_mb = len(resp.content) / (1024 * 1024)
duration_sec = len(resp.content) / 48000
print(f"Saved: {OUTPUT_PATH}")
print(f"Size: {size_mb:.1f} MB")
print(f"Duration: ~{duration_sec / 60:.1f} min")
