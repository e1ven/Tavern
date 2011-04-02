import pylzma,sys

initialstring = """
<PLURIC_CONTAINER>
<SERVER>
<TIME_SEEN>2011-04-01T01:53Z</TIME_SEEN>
<SIGNATURE>hsfgdafsyzfrseurszxfdsaEafwyd...</SIGNATURE>
</SERVER>
<SERVER>
<TIME_SEEN>2011-04-01T02:01Z</TIME_SEEN>
<SIGNATURE>ABCDEFG...</SIGNATURE>
</SERVER>

<POSTID-SHA512>3bf1683d7120a2e4482919ddefaeaa1db20ce4013c563e2f1d7f96ebde186dde80a7abe231458a7fd587d884585692a42e31f5b99932dfe90922e3fdca830a54</POSTID-SHA512>

<AUTHORITY> 400993485910747473038382868614...</AUTHORITY>
<AUTHORITY> 991921353197822591619597987982...</AUTHORITY>

<SENDER_SIGNATURE>ZYXABC...</SENDER_SIGNATURE>
<MESSAGE>

<TOPICTAG>Startrek</TOPICTAG>
<TOPICTAG>TV Shows</TOPICTAG>

<TO>90751171059740188244</TO>
<REGARDING>fa200fc2bbb11cfb2349668826685b5ec481d3555895877b5dd60d9981f411c665b2867023c61838cb78caf020ec61517aa3880ee225784fce6c560ecafeafaa</REGARDING>

<COORDS>29.199505,-90.041242</COORDS>

<AUTHOR>
<FROM>rsa AAAAB3NzaC1yc2EAAAA...</FROM>
<ABOUT>0cb128a753dec8d8d56eedc41e43083d02ec365407ca827fac7b18745eefa282ab6df1c8b97ddaed8b57ba87225bc6a0096c03effd71f8c68aea87db9fea4a43</ABOUT>
<PICTURE>84bf48ec3c1260b500919534e644608c513d2661ff6c43e93851bfb19826ce6949f59a438876fef752843823510e02c4eef8bf6b393b7879a1c28b3fef159df7</PICTURE>
<CLIENT>Pluric for Android</CLIENT>
<VERSION>1.0.0</VERSION>
</AUTHOR>

<SUBJECT>Birthright, Part 1</SUBJECT>
<BODY>
WARNING:  This article contains spoilers for "Birthright, Part I", the latest
TNG offering.  As usual, if you're not willing to be spoiled, don't blame me for it if you choose to read further.  :-)

The Enterprise is orbiting near Deep Space Nine, there to assist Bajor in
aqueduct repair.  While Picard, Crusher, Geordi and Worf are stationside,
Data goes to sickbay to investigate a power drain and finds Dr. Julian
Bashir, DS9's chief medical officer, trying to figure out the inner workings
of a field generator found in the Gamma quadrant.  Data points out that
despite his needs, Bashir cannot use the Enterprise sickbay for his purposes.
As an alternative, however, Data offers an analysis in Engineering, which
Bashir happily accepts, adding that he didn't expect Data (whom he finds fascinating) to be so "personable".


Meanwhile, Worf is accosted on the station by Jaglom Shrek, who claims to
have information to sell about Worf's father, Mogh.  Mogh, Shrek claims, was
not killed at Khitomer, but instead captured and taken to a secret Romulan
prison camp, the location of which Shrek will divulge for a price.  Worf,
however, snarls that Mogh would never let himself be captured, threatens Shrek for spreading lies, and stalks off.


Returning to the Enterprise, Worf remains in a very ill humor, snapping at an
ensign for a minor mistake and accidentally breaking a table in his quarters.  
Troi decides to find out what's bothering him ("or would you like to break
some more furniture?"), and eventually points out that despite Worf's
concerns over honor (among other things, the shame of Mogh's capture would
place a "burden of guilt" on both Worf and Alexander), he cannot let the
issue pass without trying to verify it.  She leaves him to think about his situation.


In Engineering, Data, Bashir and Geordi begin connecting up the generator for
tests, while Bashir plies Data with questions about his "ordinary"
properties, such as whether he breathes or grows his hair.  Bashir notes that
Data's creator went to great lengths to _humanize_ Data, and Bashir finds
that very interesting indeed.  Shortly thereafter, the generator overloads
and sends out a plasma shock that strikes Data full force.  Data collapses,
and has a vision of himself walking down an Enterprise corridor and finding a blacksmith -- a blacksmith with the face of a young Dr. Soong.


Upon his reactivation after the shock, Data tells Geordi and Bashir of his
vision.  No rational explanation can be found for his memories, so Data
chooses to treat it as an almost mystical experience.  He first turns to
Worf, asking Worf of a similar vision he might have had once and describing
his own.  Worf responds that Data *must* find the meaning of the vision,
because for Klingons, "nothing is more important than receiving a revelation
about your father."  Worf continues, but begins aiming his points inwards, saying that no matter what your father has done, "you must find him."


Worf returns to the station and finds Shrek.  He tells Shrek that he will pay
for the information, but *after* it has been verified -- and that Shrek will
take him there.  Further, he tells Shrek that if there is no prison camp,
Shrek will die.  Shrek takes him to the prison planet, but remains closemouthed about his reasons and the source of his information.


Data, meanwhile, talks to Picard about his experiences and his attempts to
interpret them.  After Picard advises him to start looking within *himself*
for the vision's meaning rather than into other cultures, Data returns to his quarters and begins to paint -- and paint, and paint...


Worf is dropped off and begins to travel through the dense jungle towards the
camp.  He eventually happens upon a young Klingon girl bathing.  She attempts
to flee, but he catches her and asks her to bring him to the camp.  She
reacts with puzzlement to his claim that he will take them "home", but does not give him away when a Romulan comes to get her...


Back on the Enterprise, Geordi sees Data's work, now numbering 23 paintings.  
The images in Data's paintings have expanded to include things not seen in the
vision:  smoke rising from water, a bird's wing, and so forth; and Data
believes that the only way to solve the mystery is to recreate his collapse
and let the vision continue to its end.  Despite the danger, Geordi agrees, and the experiment begins.  Data begins to dream...


He finds Soong again, only to find that he's forging a bird's wing.  He
places the wing in a bucket of water, which steams -- and when it clears, a
living bird sits on the table, then flies off.  "This vision is different..." muses Data.


"Of course it's different!"  Data looks over, to find himself and Soong now
standing on the bridge, surrounded by Data's possessions.  "It's never the
same ... always changing ... it doesn't make sense!"  Soong calls Data's
vision "a beginning.  Still a little grounded in the mundane, but showing promise."


"I do not understand."  "You're not supposed to.  No man should know where
his dreams come from!  It spoils the mystery -- the fun."  Soong walks right
up to Data and takes his face in his hands.  "I'm proud of you, son; I wasn't
sure you'd ever develop the cognitive abilities to make it this far.  But if
you're _here_ -- if you can _see_ me -- you've crossed over the threshold of
being a collection of circuits and subprocessors, and have started a wonderful journey."


"What type of journey?"  Data now finds himself on a lab table, although
still on the bridge.  "Think of it ... think of it as an empty sky," replies Soong.


"I do not understand."  "Shh.  Just dream, Data -- *dream*."  Soong bends down low and whispers faintly, "Data -- _you_ are the bird."


Data's vision changes, and he finds himself seeing images of flying, swooping
through the corridors of the Enterprise, passing Soong, and soaring out into space...


...and Data awakes in Engineering.  He later discusses with Bashir his
findings that the "dreams" were created by circuits Soong designed that were
intended to be activated by a certain level of awareness, but that have now
been activated early by the plasma shock.  He intends to "dream" every night to see what occurs.


Worf, meanwhile, reaches the prison camp undetected.  He enters, and finds a
group of Klingons engaging in what could almost be termed a Klingon
spiritual.  The apparent leader of that group leaves for another room, and Worf grabs him and forces him to answer some questions.


Worf finds first that Mogh was killed in battle at Khitomer, but that L'Kor
and his group were captured and brought to the camp.  73 now live there, and
Worf intends to bring them all home.  L'Kor, however, says that Worf does not understand and that he must speak with the others.


"I knew your father well, Worf -- and I remember you.  A boy, barely able to
lift a batlekh.  Once, your father insisted that we take you on the ritual
hunt.  You were so eager, you tried to take the beast with your bare hands.   It mauled your arm."

Worf's glare softens.  "I still have the scar -- I _do_ remember you now."


"You should not have come here, Worf."  "I do not understand."  "You should not have come."


Other Klingons enter and say that Worf must leave.  L'Kor, however, says
that it's already too late, and that he would tell others.  They grab Worf, who breaks free and begins to flee -- only to be caught by Romulan guards.

"We are not leaving here, Worf -- and neither are you."

Freeze frame.

TO BE CONTINUED.
Whew. So much for trying for a short synopsis. :-) Now, onwards to commentary.


Off the bat, I should say that the only thing keeping this show from being another solid 10 (lots of those lately...as I said, they're on a roll) is the actual mechanics of getting Worf from DS9 to the prison planet and his subsequent trap. It may lead to good stuff in part II, but it was all far too convenient -- and having recently been burned by implausibilities in "Chain of Command, Part I", I'm quite leery of another one. Among those conveniences:


-- Why is it that Worf could just up and leave without anyone on the Enterprise knowing, caring, or leaving backup plans in case something goes wrong?


-- Why is it that a planet so close (assuming the plots are proceeding at the same rate, we're talking at most 24 hours away from DS9) to Bajor is suddenly on the edge of *Romulan* space?


The former is correctable, and it's very possible that we'll see that it was indeed thought of in part II. If that happens, I'll be very impressed, though I still prefer hints being dropped in advance, like we saw in "The Defector"; the final plot twist there was foreshadowed and *still* caught me utterly flatfooted. The latter, however, is a side issue relating to why this had to take place on DS9 in the first place -- and I'd argue that aside from a bit of "crossover hype", there was no reason for it, really. (On the other hand, it meant we got to see a *lot* of Siddig El Fadil, and I don't particularly mind that.)

Anyway:

So far, "Birthright", like "Face of the Enemy", seems to reflect TNG returning, at least occasionally, to a multi-plot approach. However, both of the above examples have something in common that many early multi-plot TNG shows do not: the plotlines at least relate to each other, and at most actually intertwine.

Here, there's certainly a common theme -- that of seeking out one's father. The two plots dovetail, however, in the Data/Worf scene in Ten-Forward. While that scene is not, in my opinion, the best scene in the episode, it's among the most critical -- and did a good job of setting *both* halves of the story onto the courses they took for the remainder of the hour. And again, even though there were better scenes, it *was* awfully good; if nothing else, it's a decidedly interesting change of pace to have Worf get so introspective.

The above theme, that of fatherhood (and family, to some degree) is a surprise to see, not from TNG, but from Brannon Braga in particular. Family-centered stories have nearly always been Ron Moore's particular "specialty" (especially *Klingon* family stories) -- this is, after all, the same person who wrote "Family" and "The Defector", and much of "Reunion". I don't particularly mind being surprised at the writing credit, though, as long as the one surprising me is as adept as the one he or she is replacing -- and given both Moore's and Braga's track records, that's no problem here.

One thing in the show that *did* very definitely play to Braga's strengths was the dialoguing, both incidental and crucial. Troi was the strongest I've seen her be as _herself_ (as opposed to "Face of the Enemy") in a long while, despite only having one scene. I'm not so sure her particularly sardonic points ("Did the table do something wrong?") would be applicable in *all* her counseling situations, but they did a good job at getting through to Worf. More incidental points, such as Geordi and Worf's attempted meal on DS9, were simply amusing, but in appropriate ways throughout.

Perhaps due to the implausibilities in the Worf situation, I found the "Data's vision" subplot far more interesting. The second dream sequence was particularly notable, of course, but that's not a great surprise -- even when Winrich Kolbe's had problems with directing routine scenes, the weird ones nearly always worked, and Spiner *still* does a great Dr. Soong. What got to me nearly as much, though, was the scene of him beginning to be "inspired". (Obsessed is more like it. Even for Data, that look was of an awfully single-minded android.) Picard provided a nice motivating force, and we got to see Data being successfully creative in one of the most vivid ways possible -- dreaming.

I'm not sure where the Data plotline is going to go in part II, though (and given past history, I, alas, do not expect to ever see a trace of it *after* part II of "Birthright"). I will admit, though, that when the point was made that these dream-circuits were activated prematurely, before Data had developed enough to do it himself, my first thought was of a situation set up in Donaldson's "Thomas Covenant" trilogies -- "uh-oh," I thought, "Data's found the Second Ward without mastering the First." Something tells me there may be unpleasant consequences to this early discovery. (Those who've been reading my reviews for a couple of years know that I've seen parallels to bits and pieces of the series before. Those who have absolutely no idea what I'm talking about are advised to ask. :-) )

That said, a few words on the guest stars. First, I found Dr. Bashir's guest shot here very effective -- not necessarily enough to justify the artificial nature of setting the framing device on DS9 in the first place [particularly when he's the *only* DS9 regular we see or hear], but nice. His reaction to Data seemed very well in line with Bashir's character, both in his fascination and his uncanny ability to put his foot in his mouth. :-)

Second, while James Cromwell was no big deal as Shrek (quite acceptable, but unspectacular), Richard Herd's short turn so far as the Klingon L'Kor was extremely nice. I don't know exactly what role he's going to be playing as the plot unfolds, but I already feel somewhat like I know the *character*, thanks to his and Worf's shared memories of Worf's childhood. Nice. (Jennifer Gatti, on the other hand, may not be as effective in whatever role she plays -- while we didn't get much of a chance to tell, I wasn't that impressed with what I saw, and I'm not talking about the bathing sequence.)

Now, a couple of very quick short takes:

-- Given Troi's actions both here and in "The Emissary" way back when, I have to ask: Does she have some sort of warning sensor in her office that goes off whenever Klingons break glass tables? And for that matter, hasn't the Enterprise support staff realized that glass tables are a *bad* idea in Klingon quarters? :-)

-- While Picard was examining aqueduct layouts in his ready room, it looked for all the world like the setup for a covert "Tetris" game. One wonders -- does Picard ever decide to blow off time and play games or read the 24th-century equivalent of Usenet in his ready room? :-)

That should about cover it. All in all, I was quite pleased with what I saw, and if part II can both continue this part's strengths and explain its implausibilities, we'll have a very strong winner on our hands. So, the numbers:

Plot: 7. Some general artificialities in putting the situation on DS9 in the first place, and in getting Worf trapped as well. Plot Handling: 10. Sharply done, and possibly the best work I've seen from Kolbe in directing. Characterization: 10. Marvelous.

TOTAL: 9. Nice work yet again -- let's keep this running.

NEXT WEEK:

Looks like Worf *really* better have a backup plan.


Tim Lynch (Harvard-Westlake School, Science Dept.)
BITNET:  tlynch@citjulie
INTERNET:  tly...@juliet.caltech.edu
UUCP:  ...!ucbvax!tlynch%juliet.caltech....@hamlet.caltech.edu
"No man should know where his dreams come from!  It spoils the mystery, the
*fun*."
                        -- Dr. Soong
--
Copyright 1993, Timothy W. Lynch.  All rights reserved, but feel free to ask... 
</BODY>

<BINARY>8f5454abbdb17c3ad4b98228eab1ff5e9f0ad6d298a2fa4b5100c744cab0741d5eb11e558fb8604b8a5d5ad60d80b6e3a208c7139a7a4d9614690455467f0b9e</BINARY>
<BINARY>d2a0d25b624638797e4e34be9cef1a8ed58699406af9366764049073a33f14001a0a2fe9e954876c3680752a56add5b7da2038c8dc8bb7820e72f4c255b64348</BINARY>


</MESSAGE>

</PLURIC_CONTAINER>"""
compressed = pylzma.compress(initialstring,dictionary=27,fastBytes=255)
pylzma.decompress(compressed)

print "Compressed size " + str(sys.getsizeof(compressed))
print "Full Size " + str(sys.getsizeof(initialstring))

f = open('workfile', 'w')
f.write(compressed)
f.close()
