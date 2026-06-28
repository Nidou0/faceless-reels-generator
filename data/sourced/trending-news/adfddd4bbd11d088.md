Marcin Wichary

2 February 2015 / 1,800 words

Originally published in Medium Engineering

# The curious case of the disappearing Polish S

## One keyboard bug three decades in the making

A few weeks ago, someone reported this to us at Medium:

“I just started an article in Polish. I can type in every letter, except Ś. When I press the key for Ś, the letter just doesn’t appear. It only happens on Medium.”

This was odd. We don’t really special-case any language in any way, and even if we did… out of 32 Polish characters, why would this random one be the only one causing problems?

Turns out, it wasn’t so random. This is a story of how four incidental ingredients spanning decades (if not centuries) came together to cause the most curious of bugs, and how we fixed it.

## 
			Ingredient 1/4:

			Polish language
			

Polish is the second most-used Slavic language, right after Russian and just before Ukrainian. In contrast with those two, however, and similar to Western European languages such as German or French, Polish uses the English/Latin alphabet with a few customizations.

This is the base English alphabet, largely the same as a classic Latin/Roman alphabet:

Original Polish words never contain Q, V or X, although we keep them for Latin and other borrowed words:

In exchange for those three, however, Polish adds nine additional diacritics using Latin characters as their base, all in relatively common use:

Starting in the early 20th century, typewriters needed to accommodate the extra 9 letters. If you compare an American typewriter with a Polish one:

…and look at the right side of the keyboard, you can see two of the diacritics – Ł and Ż – promoted to separate keys, and the rest sharing keys with digits. (Typists were encouraged to assemble uppercase versions of seven remaining letters by typing a Latin character, backspacing, and then overwriting an accent to “simulate” the proper letter. This was not uncommon during typewriter times.)

To find room for the extra letters, typewriters needed to dispense with some punctuation, most notably semicolons (comma + backspace + colon), and parentheses (replaced in common use by slashes).

## 
			Ingredient 2/4:

			Communism
			

For someone interested in the early personal computing in the 1980s, Communism in Poland meant two things:

- not a lot of disposable income,
- forbidden commercial importing of computers from the West (individual importing was still possible, assuming you had enough foreign currency and some means of acquiring it).

I grew up in Poland. My first computer – the glorious Atari 800XL – was an original 1979 technology, repackaged in 1983. I got it, secondhand, in 1986.

This wasn’t unique. Technology was delayed on that side of the Iron Curtain; most computers were imported from the West. Prohibited commercial importing meant that for the longest time there was no commercial entity that could prepare computers for use in Poland. Foreign computers arrived with original instructions, untranslated software, and American keyboards like this one:

While France, Germany, and other countries got their early PCs with customized keyboards whose layouts mirrored closely the typewriters that came before…

…in Poland, we had to find another way of inputting the extra 9 diacritics unique to our language.

Our extra characters might look very much like Latin equivalents, and amount to only about 8% of letter distribution (you will hate them when playing Scrabble), but they are important. You can’t just swap them around. Consider these two similar phrases:

Perfectly interchangeable, right? Well, not quite:

There are more examples like that. As it happens, in those early PC days, I was even happy that my full name, Marcin Kazimierz Wichary, did not come with any diacritics that would complicate my life.

Surely, there’s something that can be done, though? Back to the keyboard:

We cannot modify it in any way since that’d require messing with hardware, but we can still try to find a clever solution. There are two modifier keys – Ctrl (where today’s Caps Lock is), and Alt. Ctrl was already used as a common shortcut key, even before CtrlC and CtrlV became typical vessels for copy and paste. But Alt was relatively uncommon. And thus, a de facto standard was born, assigning 8 of our diacritics to their Latin counterparts, and one to something nearby:

People started calling the older layout “typist’s,” and the new invention “programmer’s,” either because early PC users were mostly programmers, or because it preserved all the punctuation symbols that were often used in programming.

The new layout was an ergonomic nightmare – look at how many of those letters are very close to the solitary Alt on the left, and need to be pressed using the same hand – but it was easy to understand and did not require any expensive hardware modifications or even cheap ones (for example stickers). It stuck. A few other nearby countries – Romania, then-Czechoslovakia – came up with similar schemes.

The setup was so successful that even when, a decade later, proper typist’s keyboards started appearing, practically no one would switch to them, mirroring the ascendancy of less-than-ideal QWERTY some 80 years before.

## 
			Ingredient 3/4:

			Old habits dying hard
			

Autosaving, common today, needed to wait for the right moment. Especially in the 1980s, and even 1990s, saving your document was lengthy (powering up that floppy drive and writing to the disk took some time), would slowly wear out whatever medium you were using, and sometimes occupy CPU so intensely it couldn’t be used for anything else.

Saving by hand was then what backing up is today: a habit you needed to learn for your own good. The unlucky ones figured it out the hard way, writing for hours on a computer that had a tendency to crash cruelly and often, only to realize they forgot to save their work.

I was one of them. We all learned to press CommandS or CtrlS whenever we paused for breat