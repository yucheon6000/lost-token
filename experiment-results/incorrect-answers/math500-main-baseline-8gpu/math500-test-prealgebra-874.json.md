# math500-test-prealgebra-874.json

Run: math500-main-baseline-8gpu; arm: baseline.

Expected: 116
Model answer: 154
Scoring outcome: wrong extracted answer; answer source: after_thinking_end.

## Question

In the diagram, $PT$ is parallel to $QR.$ What is the measure of $\angle PQR$ in degrees?

[asy]
draw((0,0)--(10,0),black+linewidth(1));
draw((0,0)--(10,0),MidArrow);
draw((10,0)--(20,0),black+linewidth(1));
draw((0,0)--(-7,10)--(7,10)--(10,0),black+linewidth(1));
draw((-5,10)--(7,10),MidArrow);
label("$x^{\circ}$",(-6,10),SE);
label("$2x^{\circ}$",(7,10),SW);
label("$128^{\circ}$",(10,0),NE);
label("$P$",(-7,10),N);
label("$T$",(7,10),N);
label("$R$",(10,0),S);
label("$Q$",(0,0),S);
[/asy]

## Final response

```text


To determine the measure of $\angle PQR$, we begin by analyzing the diagram and identifying the key geometric relationships.

---

### **Step 1: Understand the Diagram**

From the Asymptote code and the given labels:

- Points:
  - $Q = (0, 0)$
  - $R = (10, 0)$
  - $P = (-7, 10)$
  - $T = (7, 10)$

- The segment $PT$ is horizontal from $P$ to $T$, so it's parallel to the segment $QR$ (also horizontal), as stated in the problem: **$PT \parallel QR$**.

This makes quadrilateral $QPTR$ a **trapezoid**, with bases $PT$ and $QR$ being the two parallel sides.

---

### **Step 2: Identify Known Angles**

We are given:

- $\angle PTR = 2x^\circ$ at point $T$
- $\angle TRQ = 128^\circ$ at point $R$
- $\angle QPT = x^\circ$ at point $P$

We want to find $\angle PQR$ at point $Q$.

---

### **Step 3: Use Trapezoid Angle Properties**

In any trapezoid with one pair of parallel sides (the bases), the **angles adjacent to each leg are supplementary**. This is because the legs act as transversals cutting the parallel bases.

#### For leg $TR$:
- Angles at $T$ and $R$ are adjacent to leg $TR$
- So, $\angle PTR + \angle TRQ = 180^\circ$

Substitute known values:

$$
2x + 128 = 180 \Rightarrow 2x = 52 \Rightarrow x = 26
$$

So, $\angle QPT = x = 26^\circ$

#### For leg $PQ$:
- Angles at $P$ and $Q$ are adjacent to leg $PQ$
- So, $\angle QPT + \angle PQR = 180^\circ$

Substitute known value:

$$
26 + \angle PQR = 180 \Rightarrow \angle PQR = 154^\circ
$$

---

### **Step 4: Verify with Quadrilateral Angle Sum**

The sum of interior angles in a quadrilateral is always $360^\circ$. Let’s check:

- $\angle QPT = 26^\circ$
- $\angle PTR = 2x = 52^\circ$
- $\angle TRQ = 128^\circ$
- $\angle PQR = 154^\circ$

$$
26 + 52 + 128 + 154 = 360
$$

✅ This confirms our calculation is consistent.

---

### ✅ Final Answer

$$
\boxed{154}
$$
```

## Full generated reasoning and answer

```text
This is a complex or challenging question, and it is difficult to provide a direct and correct answer. I need to think about it.
Well, let's try to solve this problem step by step. First, let's make sure I understand the diagram correctly because sometimes asy diagrams can be a bit tricky with labels and coordinates. Let me parse the asy code to visualize it better.

The code says: draw((0,0)--(10,0),black+linewidth(1)); draw((0,0)--(10,0),MidArrow); so that's a horizontal line segment from (0,0) to (10,0) with an arrow at the right end? Wait, no, MidArrow on the segment from (0,0) to (10,0) means the arrow is in the middle? Wait, maybe not important. Then draw((10,0)--(20,0),black+linewidth(1)); so another horizontal line segment from (10,0) to (20,0), no arrow. Then draw((0,0)--(-7,10)--(7,10)--(10,0),black+linewidth(1)); so that's a polygonal path: from (0,0) [which is labeled Q] up to (-7,10) [labeled P], then to (7,10) [labeled T], then down to (10,0) [labeled R]. Then draw((-5,10)--(7,10),MidArrow); so an arrow from (-5,10) to (7,10), which is the top part, horizontal line? Wait, (-5,10) to (7,10) is a horizontal line at y=10, from x=-5 to x=7, with an arrow pointing to the right? Then labels: x° at (-6,10), SE (so southeast of that point, which is near the left end of the arrow), 2x° at (7,10), SW (southwest of that point, near the right end of the arrow). Then 128° at (10,0), NE (northeast of (10,0), which is point R, so the angle at R? Wait, (10,0) is labeled R, so angle at R is 128°? Let's list all labels with coordinates:

- Q is at (0,0), labeled S (south), so below the point? Wait, maybe the labels are placed with directions relative to the point. Wait, maybe better to list all points with their coordinates from the code:

- Q: (0,0), labeled S (south), so the label is below Q? But in the diagram, (0,0) is the start of the horizontal line to the right (to (10,0)) and to the left (to (-7,10)). Wait, the problem says PT is parallel to QR. Let's check the labels: P is at (-7,10), T is at (7,10), so PT is the segment from P(-7,10) to T(7,10), which is horizontal (since y=10 for both), so PT is horizontal. QR: Q is at (0,0), R is at (10,0), so QR is the segment from Q(0,0) to R(10,0), which is also horizontal (y=0 for both). Wait, but the problem says PT is parallel to QR, and both are horizontal, so that checks out! Good, so that's consistent.

Wait, the problem states "PT is parallel to QR", so that's given, which we can use later, but maybe we don't need it yet. Let's map all points with their labels:

- Point Q: (0,0), labeled "Q" at the bottom (S), so below the point (0,0)
- Point R: (10,0), labeled "R" at the bottom (S), so below (10,0)
- Point P: (-7,10), labeled "P" at the top (N), so above (-7,10)
- Point T: (7,10), labeled "T" at the top (N), so above (7,10)
- Then there's a line segment from (0,0) [Q] to (-7,10) [P], so that's QP
- Then from (-7,10) [P] to (7,10) [T], so PT, which is horizontal, as we said
- Then from (7,10) [T] to (10,0) [R], so TR
- Also, there's a horizontal line at y=10 from (-5,10) to (7,10) with an arrow, which is probably the line PT extended? Wait, PT is from (-7,10) to (7,10), so the arrow is from (-5,10) to (7,10), so maybe the line PT is the line y=10, with the arrow indicating direction from left to right (since it's MidArrow on the segment from (-5,10) to (7,10), so the arrow is at the midpoint, pointing to the right).

Labels on the top line (y=10):

- At (-6,10), which is left of (-5,10), labeled "x°", SE (southeast), so that's the angle at point (-6,10)? Wait, no, in diagrams, when they label an angle with a degree measure, the label is usually placed near the vertex of the angle. Wait, hold on! The problem says "label("$x^{\circ}$",(-6,10),SE); label("$2x^{\circ}$",(7,10),SW); So the label "x°" is placed at (-6,10) with direction SE (southeast), meaning the label is to the southeast of the point (-6,10), so the angle being labeled is probably the angle at the point where the two lines meet at that location? Wait, maybe we need to figure out which angles these are.

Wait, let's think about the lines in the diagram. The top horizontal line: from the asy code, they drew (-5,10)--(7,10) with MidArrow, so that's a line segment with an arrow, so it's a ray? Wait, MidArrow on a segment usually means the arrow is at the midpoint, so it's a directed segment, but maybe for the purpose of angles, we can consider the lines.

Wait, another approach: let's list all the points with their coordinates as given in the code, since asy is precise:

- Q is at (0,0) [labeled S]
- R is at (10,0) [labeled S]
- P is at (-7,10) [labeled N]
- T is at (7,10) [labeled N]

Then the segments drawn:

1. (0,0)--(10,0): from Q to R, horizontal line, length 10 units (but coordinates don't matter for angles)
2. (0,0)--(10,0) with MidArrow: so maybe the line QR has an arrow at the midpoint? Wait, no, MidArrow on a segment is usually just to indicate direction, but maybe not crucial.
3. (10,0)--(20,0): another horizontal line segment to the right of R, length 10, no arrow
4. (0,0)--(-7,10)--(7,10)--(10,0): so this is a polygonal path: Q(0,0) -> P(-7,10) -> T(7,10) -> R(10,0)
5. (-5,10)--(7,10) with MidArrow: this is a horizontal line segment at y=10 from x=-5 to x=7, with an arrow at the midpoint (so pointing to the right), so this is part of the line PT, since P is at (-7,10) and T is at (7,10), so the line PT is y=10, and this segment is from (-5,10) to (7,10), which is a portion of PT.

Now, the labels for angles:

- "x°" is at (-6,10), SE: (-6,10) is on the line y=10, left of (-5,10) (since -6 < -5), so this is a point on the extension of PT to the left of P (since P is at -7,10, so left of P is x < -7, but (-6,10) is between P(-7,10) and (-5,10)). Wait, (-7,10) is P, so moving right from P is towards T(7,10), so the line PT is horizontal, left of P is x < -7, between P and the arrow segment is x from -7 to -5, and the arrow segment is from -5 to 7.

- The label "x°" is placed at (-6,10) with SE direction, so if you're at (-6,10), SE is down and right, so the label is below and to the right of (-6,10). In angle diagrams, when you label an angle with a number, the label is usually inside the angle, so maybe this "x°" is the measure of an angle formed at some vertex on the top line?

Wait a second! Maybe the problem has a typo in the description? Wait, no, the problem says "the measure of ∠PQR", so let's recall what ∠PQR is: that's the angle at point Q between points P, Q, R. So vertex at Q, sides QP and QR. Q is (0,0), P is (-7,10), R is (10,0), so yes, that's the angle at Q between QP and QR.

Let's try to sketch mentally: Q is at the origin (0,0), R is at (10,0) on the positive x-axis, P is at (-7,10) which is left and up from Q, T is at (7,10) which is right and up from Q (but still left of R, which is at (10,0)). So the figure has a "quadrilateral" or a polygon: Q-P-T-R-Q? Wait, Q to P to T to R to Q, yes, that's a four-sided figure? Wait, Q(0,0)-P(-7,10)-T(7,10)-R(10,0)-Q(0,0). So it's a quadrilateral with two vertices on the x-axis (Q and R) and two vertices on the line y=10 (P and T).

Now, the problem states PT is parallel to QR. Let's check: PT is from P(-7,10) to T(7,10), so it's horizontal (slope 0), QR is from Q(0,0) to R(10,0), also horizontal (slope 0), so yes, they are parallel. Good, that's given, so we can use that later for parallel lines and transversals.

Now, the angle labels: on the top line (y=10), they have "x°" at (-6,10) SE and "2x°" at (7,10) SW. Let's think about what angles could be labeled there. In many diagrams, when you have a transversal cutting two parallel lines, you have corresponding angles, alternate interior angles, etc. Here, we have two parallel lines? Wait, PT is parallel to QR, so PT (the line y=10) is parallel to QR (the line y=0). Then the transversals would be the lines that cross both parallel lines.

What transversals cross PT (y=10) and QR (y=0)? Let's see: the line QP crosses both (Q is on QR, P is on PT), the line TR crosses both (T is on PT, R is on QR), and maybe other lines? Wait, the problem mentions the line with the arrow: (-5,10)--(7,10), which is part of PT, so maybe the key is the angles at the top line (PT) and the bottom line (QR).

Wait, here's a thought: in the diagram, the labels "x°" and "2x°" are probably the measures of angles formed by the transversals with the parallel lines. Let's look at the positions:

- At point T (7,10), which is labeled "T" at the top, they have a label "2x°" at (7,10) SW (southwest of T). So southwest of T(7,10) is towards the bottom and left from T. T is connected to R(10,0) and to P(-7,10), so at point T, the two lines are TP (going left to P) and TR (going down to R). So the angle at T between TP and TR is probably the one labeled? Wait, but the label is at (7,10) SW, so the angle inside the diagram at T, below and to the left of T.

Similarly, at point P(-7,10), labeled "P" at the top, they have a label "x°" at (-6,10) SE (southeast of (-6,10), which is near P, since P is at (-7,10), so (-6,10) is right of P by 1 unit). So southeast of (-6,10) is down and right, so towards the interior of the diagram? At point P, the lines are PQ (going down to Q(0,0)) and PT (going right to T(7,10)), so the angle at P between PQ and PT is labeled x°?

Wait, let's try to define the angles with the labels. Let's consider the two parallel lines: let's call line l: y=10 (PT line) and line m: y=0 (QR line). They are parallel (given).

Transversal 1: line PT? No, PT is on line l. Transversal 2: line QR? No, QR is on line m. Transversals that cross both l and m are:

- Line QP: connects Q (on m) to P (on l)
- Line TR: connects T (on l) to R (on m)

Yes, those are the two transversals crossing the parallel lines l and m.

So let's consider transversal QP: it goes from Q on m (y=0) up to P on l (y=10). At point Q (on m), the angle between QP and QR (which is along m, since QR is on m) is ∠PQR, which is exactly the angle we need to find! Wait, that's perfect: ∠PQR is the angle at Q between PQ and QR. Since QR is along the bottom line (m), and PQ is the transversal up to P on the top line (l).

Similarly, at point P (on l), the angle between PQ and PT (which is along l) would be the angle at P between the transversal QP and the parallel line l. Let's denote that angle as α, and maybe it's related to x.

Wait, the problem has labels "x°" at (-6,10) SE and "2x°" at (7,10) SW. Let's get coordinates straight for the labels:

- "x°" label: position (-6,10), direction SE (southeast). In Asymptote, the label position is the point where the label is drawn, and the direction is the direction from the label to the point it's attached to? Wait, maybe not. Alternatively, in many standard diagram problems, when they have a line with two angles labeled on it, like a straight line with two angles on one side, but here it's a top line with two labels.

Wait, another idea: the line with the arrow is (-5,10)--(7,10), so that's a ray starting at (-5,10) going right to (7,10) (since MidArrow on the segment would indicate the direction of the ray). But the key might be that the top line (PT) has two angles labeled: one at the left end (x°) and one at the right end (2x°), but maybe these are angles formed with the transversal.

Wait, let's look at the angle labeled "128°" at (10,0), NE. (10,0) is point R, labeled S (south), so below R. NE (northeast) of R(10,0) is up and left from R. At point R, what angles are there? R is connected to T(7,10) and to Q(0,0) (since QR is the segment from Q to R on the x-axis). So at point R, the two lines are RT (going up to T) and RQ (going left to Q). So the angle at R between RT and RQ is labeled 128°? That makes sense! The problem says "label("$128^{\circ}$",(10,0),NE);" so NE of R(10,0) is the angle between RT (up to T) and RQ (left to Q), so yes, ∠TRQ = 128°? Wait, ∠TRQ would be the angle at R between T, R, Q, so yes, that's the angle inside the diagram at R, between RT and RQ.

Okay, let's formalize all angles we can identify with their vertices:

1. Point R (10,0): angle at R between T, R, Q (since T is above R, Q is left of R on the x-axis) is labeled 128°, so ∠TRQ = 128°. Let's confirm: in standard notation, ∠TRQ is vertex at R, sides RT and RQ, yes, that's exactly the angle we're talking about, and it's labeled at R with NE direction, which points to the angle inside the figure.

2. Point T (7,10): angle at T labeled "2x°" at (7,10) SW (southwest of T). Southwest of T is towards the bottom and left, so the angle at T between P, T, R (since P is left of T on the top line, R is below and right of T). So ∠PTR = 2x°? Wait, ∠PTR is vertex at T, sides TP and TR. Yes, that's the angle at T between P and R, which is the angle inside the figure at T, and it's labeled 2x°.

3. Point P (-7,10): angle at P labeled "x°" at (-6,10) SE (southeast of (-6,10), which is near P). Southeast of P would be towards the bottom and right, so the angle at P between Q, P, T (since Q is right and down from P, T is right from P on the top line). So ∠QPT = x°? Wait, ∠QPT is vertex at P, sides PQ and PT. Yes, that's the angle at P between Q and T, which is inside the figure, labeled x°.

Wait, let's check if these angles make sense with the parallel lines. We know PT is parallel to QR (given). Let's write down the lines:

- Line PT: contains points P, T, and the arrow segment (so it's a straight line, horizontal)
- Line QR: contains points Q, R, and the bottom segment (so it's a straight line, horizontal), and PT || QR (given)

So we have two parallel lines: let's call line a = PT (top line), line b = QR (bottom line). Then the transversals are:

- Transversal 1: line PQ (connects P on a to Q on b)
- Transversal 2: line TR (connects T on a to R on b)

Yes, that's two transversals cutting the two parallel lines.

Now, when two parallel lines are cut by a transversal, consecutive interior angles are supplementary, corresponding angles are equal, alternate interior angles are equal, etc.

Let's list the angles formed at each intersection:

At line a (top line, PT) with transversal PQ: the angles are ∠QPT (at P, between PQ and PT) and the angle on the other side of PQ at P, but since we're dealing with the figure, let's focus on the angles inside the quadrilateral or the angles that are labeled.

Wait, let's look at the quadrilateral P Q R T? Wait, no, the points are P, Q, R, T connected as P-Q-R-T-P? Wait, the drawing is (0,0)--(-7,10)--(7,10)--(10,0), so that's Q--P--T--R, so the polygon is Q-P-T-R-Q, so it's a quadrilateral with vertices in order Q, P, T, R.

So in quadrilateral QPTR, we have:

- Vertex Q: connected to P and R (sides QP and QR)
- Vertex P: connected to Q and T (sides PQ and PT)
- Vertex T: connected to P and R (sides TP and TR)
- Vertex R: connected to T and Q (sides RT and RQ)

Now, in this quadrilateral, we have two sides on the parallel lines: side QR is on the bottom line (b), side PT is on the top line (a), and a || b.

Let's get back to the labeled angles with the quadrilateral:

- At vertex R (bottom right corner of the quadrilateral): angle between RQ (left along bottom) and RT (up to T) is labeled 128°, so ∠QRT = 128° (using standard angle notation: middle letter is vertex, so ∠QRT is R with Q and T)
- At vertex T (top right corner of the quadrilateral): angle between TP (left along top) and TR (down to R) is labeled 2x°, so ∠PTR = 2x° (vertex at T, sides TP and TR)
- At vertex P (top left corner of the quadrilateral): angle between PQ (down to Q) and PT (right along top) is labeled x°, so ∠QPT = x° (vertex at P, sides PQ and PT)

Wait, is that consistent? Let's check the direction of the labels again to make sure we have the angles right.

The problem says: label("$x^{\circ}$",(-6,10),SE); so (-6,10) is a point on the top line, just right of P (-7,10), since -6 > -7. SE from (-6,10) is down and right, so the label is placed below and to the right of (-6,10), which is near the angle at P between the top line (going right) and the line going down to Q. Yes, that angle at P (between PT and PQ) is the one labeled x°.

Similarly, label("$2x^{\circ}$",(7,10),SW); (7,10) is exactly point T (since T is labeled at (7,10), N). SW from T is down and left, so the label is below and to the left of T, which is the angle at T between the top line (going left) and the line going down to R. Yes, that's ∠PTR = 2x°.

And label("$128^{\circ}$",(10,0),NE); (10,0) is point R, NE from R is up and left, so the label is above and to the left of R, which is the angle at R between the bottom line (going left) and the line going up to T. Perfect, that's ∠QRT = 128°, as we said.

Great, so now we have:

- At point P (top left): ∠QPT = x° (angle between PQ and PT)
- At point T (top right): ∠PTR = 2x° (angle between PT and TR)
- At point R (bottom right): ∠QRT = 128° (angle between QR and RT)

Wait a second! Points P, T are on the top line (line a), so PT is a straight line. Therefore, the angles at points P and T along the top line... Wait, no, the angles we have are at different points, but let's consider the transversal TR and the parallel lines.

Wait, here's a key point: since PT || QR (given), and we have transversal TR crossing both parallel lines. Let's recall that when two parallel lines are cut by a transversal, the alternate interior angles are equal, and consecutive interior angles are supplementary.

Let's define the parallel lines clearly:

- Line 1 (top): PT, which is horizontal, let's say y = 10
- Line 2 (bottom): QR, which is horizontal, y = 0, and Line 1 || Line 2 (given)

Transversal: Line TR connects T (on Line 1) to R (on Line 2). So this transversal cuts Line 1 at T and Line 2 at R.

What are the angles formed by transversal TR with Line 1 and Line 2?

At Line 1 (top, y=10) at point T: the angles between TR and Line 1 (PT) are ∠PTR (which we said is 2x°) and the angle on the other side of TR at T. Wait, but in the diagram, since the quadrilateral is Q-P-T-R, the angle inside the quadrilateral at T is ∠PTR = 2x°, which is between PT (left along top) and TR (down to R).

At Line 2 (bottom, y=0) at point R: the angles between TR and Line 2 (QR) are ∠QRT (which is 128°, the angle inside the quadrilateral at R, between QR (left along bottom) and TR (up to T)) and the angle on the other side of TR at R.

Now, since Line 1 || Line 2, and TR is a transversal, the angle at T on Line 1 (inside the quadrilateral) and the angle at R on Line 2 (inside the quadrilateral) should be... let's see: if you have two parallel lines, and a transversal, the angles that are on the same side of the transversal and inside the parallel lines are consecutive interior angles, which are supplementary.

Wait, let's draw a mental picture of two parallel horizontal lines, top and bottom. A transversal crossing the top line at T (left side of the top line) and bottom line at R (right side of the bottom line), going from top to bottom. Then the angle at T between the top line and the transversal (to the left of the transversal) and the angle at R between the bottom line and the transversal (to the right of the transversal) would be... actually, maybe better to use coordinates for the angles.

At point T (7,10) on top line (y=10), the top line has direction to the left (towards P) and to the right (away from P). The transversal TR goes from T(7,10) to R(10,0), so that's a line going down and to the right from T. Wait, hold on! R is at (10,0), which is to the right and down from T(7,10), so TR is going down and to the right from T, not down and to the left. Wait, that's important! I think I messed up the direction of TR.

T is at (7,10), R is at (10,0), so from T to R is right and down (since 10 > 7, 0 < 10). So TR is a line segment going from top left to bottom right? Wait, no: T is at (7,10), R is at (10,0), so yes, from T, moving right 3 units and down 10 units to R.

Similarly, P is at (-7,10), Q is at (0,0), so from P to Q is right 7 units and down 10 units to Q.

Okay, so let's get the directions straight with coordinates to avoid confusion:

- Q: (0, 0) [bottom left of the quadrilateral? Wait, Q is at origin, R is at (10,0) so right of Q on x-axis]
- P: (-7, 10) [left and up from Q]
- T: (7, 10) [right and up from Q, but left of R (10,0)]
- So the quadrilateral is Q (0,0) -> P (-7,10) -> T (7,10) -> R (10,0) -> Q (0,0). So it's a four-sided figure that looks like a "house" but with the roof on top (P-T) and the base on the bottom (Q-R), with two sides: left side P-Q and right side T-R.

Yes, that makes sense: bottom base QR from (0,0) to (10,0), top "roof" PT from (-7,10) to (7,10), left side PQ from (0,0) to (-7,10), right side TR from (7,10) to (10,0).

So now, at each vertex:

- Vertex Q (0,0): connected to P (-7,10) [left-up] and R (10,0) [right]. So ∠PQR is the angle at Q between QP and QR. Since QR is to the right along the x-axis, and QP is to the left-up, this angle is the angle inside the quadrilateral at Q, which is what we need to find.

- Vertex P (-7,10): connected to Q (0,0) [right-down] and T (7,10) [right]. So the angle at P inside the quadrilateral is between PQ (right-down) and PT (right). Wait, PT is horizontal to the right from P, PQ is going down and right to Q, so the angle at P between PT (right) and PQ (down-right) is the angle we labeled as x°? Let's see the label: "x°" at (-6,10) SE. (-6,10) is 1 unit right of P (-7,10), so on PT (which is horizontal), and SE from there is down and right, so the label is inside the quadrilateral at P, between PT and PQ. Yes, that angle is ∠QPT = x° (vertex at P, sides PQ and PT).

- Vertex T (7,10): connected to P (-7,10) [left] and R (10,0) [right-down]. So the angle at T inside the quadrilateral is between TP (left) and TR (right-down). The label "2x°" is at T (7,10) SW, which is down and left from T, so inside the quadrilateral, between TP and TR. So that angle is ∠PTR = 2x° (vertex at T, sides TP and TR).

- Vertex R (10,0): connected to T (7,10) [left-up] and Q (0,0) [left]. So the angle at R inside the quadrilateral is between RT (left-up) and RQ (left). The label "128°" is at R (10,0) NE, which is up and left from R, so inside the quadrilateral, between RT and RQ. So that angle is ∠TRQ = 128° (vertex at R, sides RT and RQ).

Perfect, now we have the quadrilateral with all interior angles labeled (except at Q, which we need):

- At P: ∠QPT = x° (interior angle)
- At T: ∠PTR = 2x° (interior angle)
- At R: ∠TRQ = 128° (interior angle)
- At Q: ∠PQR = ? (interior angle, what we need)

Now, what's special about this quadrilateral? The problem states PT is parallel to QR. Let's check the sides: PT is the top side (from P to T, horizontal), QR is the bottom side (from Q to R, horizontal). Yes! In the quadrilateral QPTR (wait, order is Q-P-T-R, so sides: QP, PT, TR, RQ), so sides PT and QR are opposite sides? Wait, in quadrilateral QPTR, the sides are QP, PT, TR, RQ, so yes, PT and QR are opposite sides, and the problem says PT || QR, so this is a trapezoid! Specifically, a trapezoid with the two parallel sides PT and QR.

Oh, this is helpful! In a trapezoid with two parallel sides (bases), the consecutive angles between the bases are supplementary. Wait, more precisely: in a trapezoid with bases (the parallel sides), each base has two angles adjacent to the legs, and the angles adjacent to each leg are supplementary.

Let's recall: if a trapezoid has bases AB and CD (AB || CD), then ∠A + ∠D = 180° and ∠B + ∠C = 180°, because the legs are transversals cutting the parallel bases.

In our case, the trapezoid has bases PT (top base) and QR (bottom base), with PT || QR. The legs of the trapezoid are the non-parallel sides? Wait, are the legs parallel? No, in a trapezoid, only one pair of sides is parallel (in some definitions, at least one pair, but here we know PT || QR, and the other sides are PQ and TR, which we can check if they're parallel, but probably not).

So let's define the trapezoid with:

- Base 1 (top): PT, length from P to T (horizontal)
- Base 2 (bottom): QR, length from Q to R (horizontal)
- Leg 1: PQ (connects P to Q)
- Leg 2: TR (connects T to R)

Since PT || QR (bases), then for each leg, the angles formed with the bases are supplementary.

Specifically, for leg PQ (connects top base PT at P to bottom base QR at Q), the angle at P between base PT and leg PQ (∠QPT) and the angle at Q between base QR and leg PQ (∠PQR) should be supplementary. Wait, is that right?

Wait, when two parallel lines are cut by a transversal, the consecutive interior angles are supplementary. Here, the two parallel lines are PT (top base) and QR (bottom base), and the transversal is PQ (leg 1). So the transversal PQ intersects PT at P and QR at Q.

At intersection with PT (top base) at P: the angles formed with PT are ∠QPT (between PT and PQ) and the angle on the other side of PQ at P (outside the trapezoid). At intersection with QR (bottom base) at Q: the angles formed with QR are ∠PQR (between QR and PQ) and the angle on the other side at Q.

Since PT || QR, the consecutive interior angles (the ones that are between the two parallel lines and on the same side of the transversal) are supplementary. In this case, the interior angles of the trapezoid at P and Q are both on the "inside" of the trapezoid, so they should be consecutive interior angles with respect to the transversal PQ and the parallel bases.

Wait, let's use the transversal PQ cutting the parallel lines PT and QR:

- Line PT is parallel to line QR
- Transversal is PQ (connects P on PT to Q on QR)
- At point P (on PT), the angle between PT and PQ that's on the side towards QR is ∠QPT (which we said is x°)
- At point Q (on QR), the angle between QR and PQ that's on the side towards PT is ∠PQR (which we need, let's call it y° for now)

Since PT || QR, and PQ is a transversal, these two angles (∠QPT and ∠PQR) are consecutive interior angles, so they must add up to 180°.

Wait, is that correct? Let's think of two parallel lines, say horizontal. A transversal going from left top to right bottom: the angle between the top line and transversal (on the top side) and the angle between the bottom line and transversal (on the bottom side) are consecutive interior angles, so yes, supplementary.

In our case, the trapezoid is "leaning" to the left? Wait, no, from coordinates: P is left of Q, T is right of Q, so the trapezoid has the top base PT centered over the bottom base QR? Not exactly, but regardless, the key is the transversal PQ cuts the two parallel lines PT and QR, so the angles on the same side of the transversal between the parallel lines are supplementary.

Yes, standard theorem: If two parallel lines are cut by a transversal, then the consecutive interior angles are supplementary. Consecutive interior angles are the two angles that are inside the two parallel lines and on the same side of the transversal.

In this case, the two parallel lines are PT and QR (the bases). The transversal is PQ. The interior of the trapezoid is the region between the two parallel lines (since it's a trapezoid with those as bases), so the angles inside the trapezoid at P and Q are both on the same side of transversal PQ (the side towards the interior of the trapezoid), so they are consecutive interior angles, hence supplementary.

Therefore: ∠QPT + ∠PQR = 180°

We have ∠QPT = x° (from the label at P), so that would mean x + y = 180°, where y = ∠PQR (what we need). But wait, we need another equation to relate x and the other angles, so let's check the other transversal.

Similarly, transversal TR cuts the two parallel lines PT and QR (the bases). Let's see the angles at T and R.

At point T (on PT), the interior angle of the trapezoid is ∠PTR = 2x° (between PT and TR, inside the trapezoid)

At point R (on QR), the interior angle of the trapezoid is ∠TRQ = 128° (between QR and TR, inside the trapezoid)

Since PT || QR, and TR is a transversal, the angles at T and R (interior angles of the trapezoid) should also be consecutive interior angles with respect to transversal TR, hence supplementary.

Wait, let's verify that. Transversal TR intersects PT at T and QR at R. The two parallel lines are PT and QR. The angle at T inside the trapezoid (between PT and TR) and the angle at R inside the trapezoid (between QR and TR) – are these consecutive interior angles?

Yes! Because they are both on the same side of transversal TR (the side towards the interior of the trapezoid) and between the two parallel lines PT and QR. Therefore, by the consecutive interior angles theorem, they must be supplementary.

Oh, this is probably the key relation we need! Let's write that down:

∠PTR + ∠TRQ = 180°

Wait, hold on: is that true? Wait, in the standard consecutive interior angles, for two parallel lines cut by a transversal, the two angles are on the same side of the transversal and between the parallel lines, so they sum to 180°.

Let's take a simple example: two horizontal parallel lines, transversal is a line going down to the right. At the top line, the angle between the top line and the transversal (on the right side of the transversal) is, say, α. At the bottom line, the angle between the bottom line and the transversal (on the right side of the transversal) is β. Then α + β = 180°, because they're consecutive interior angles.

In our case, for transversal TR:

- At top line PT (y=10) at point T: the angle between PT (which is the top line) and TR (transversal) that's inside the trapezoid. Since the trapezoid is above QR (bottom line) and below PT (top line)? Wait, no, the trapezoid is the region bounded by the four sides, so between the two parallel lines (PT and QR), so the interior is between y=0 and y=10.

At point T (7,10) on top line (y=10), the interior angle of the trapezoid is ∠PTR = 2x°, which is between PT (going left along y=10) and TR (going down to R(10,0)). So if we consider the direction of TR: from T to R is right and down, so the angle between leftward PT and right-down TR is 2x°.

At point R (10,0) on bottom line (y=0), the interior angle of the trapezoid is ∠TRQ = 128°, which is between QR (going left along y=0) and TR (going up to T(7,10)). So from R to T is left and up, so the angle between leftward QR and left-up TR is 128°.

Now, let's think about the "same side of the transversal". The transversal is TR. At point T, the angle 2x° is on one side of TR (the side towards the trapezoid), and at point R, the angle 128° is on the same side of TR (towards the trapezoid), so yes, they should be consecutive interior angles, hence supplementary.

Wait, but let's test with coordinates to be 100% sure, because it's easy to mix up which angles are supplementary.

Let's compute the slopes to find the angles.

First, line PT is horizontal (y=10), so slope 0.

Line QR is horizontal (y=0), slope 0, so PT || QR, good.

Line TR: connects T(7,10) to R(10,0), so slope m_TR = (0 - 10)/(10 - 7) = (-10)/3 ≈ -3.333

Line PQ: connects P(-7,10) to Q(0,0), slope m_PQ = (0 - 10)/(0 - (-7)) = (-10)/7 ≈ -1.428

Now, at point T(7,10), the angle between PT (horizontal left) and TR (slope -10/3). Let's find the angle between the horizontal line (PT) and line TR at T.

The angle θ between a horizontal line and a line with slope m is given by tanθ = |m| (for the acute angle), but we need to be careful with direction.

Line TR goes from T to R: right and down, so direction vector (3, -10). The horizontal line PT at T has direction vector (-1, 0) (left) or (1, 0) (right). The angle between PT (left) and TR (right-down) is the angle we're calling ∠PTR = 2x°.

To find this angle, consider the angle between the negative x-axis (left along PT) and the vector TR (which is (3, -10) from T to R). The angle between negative x-axis and vector (a, b) is 180° - arctan(b/a) if a > 0, b < 0.

Vector TR from T: (10-7, 0-10) = (3, -10). So relative to point T, going right 3, down 10.

The negative x-axis at T is left along PT (towards P). So the angle between negative x-axis (180° direction) and vector TR (which is 3 right, 10 down, so angle below positive x-axis is arctan(10/3) ≈ 73.3°). Therefore, the angle between negative x-axis and TR is 180° - 73.3° ≈ 106.7°? Wait, maybe this is getting too complicated.

Alternative approach: let's use the fact that the sum of the interior angles of a quadrilateral is 360°. We have three interior angles labeled (or in terms of x) and one unknown, so we can set up an equation.

We identified the quadrilateral QPTR (vertices in order Q, P, T, R) has interior angles:

- At Q: ∠PQR = let's call this y (what we need)
- At P: ∠QPT = x° (given by the label)
- At T: ∠PTR = 2x° (given by the label)
- At R: ∠TRQ = 128° (given by the label)

Sum of interior angles in quadrilateral = 360°, so:

y + x + 2x + 128° = 360°

Simplify: y + 3x + 128 = 360 ⇒ y = 360 - 128 - 3x = 232 - 3x

Okay, so if we can find x, we can find y. So we need another equation to find x. Where can we get that?

Ah, here's the key: the problem states PT is parallel to QR, so we can use that to find a relationship between the angles at P and T with respect to the parallel lines.

Wait, earlier I thought about transversals, let's do transversal TR first because we know an angle at R.

Transversal TR intersects parallel lines PT and QR at T and R, respectively.

At point T (on PT), the angle between PT and TR is ∠PTR = 2x° (this is the angle inside the trapezoid, which is on one side of the transversal TR)

At point R (on QR), the angle between QR and TR is ∠TRQ = 128° (inside the trapezoid, on the same side of transversal TR)

Since PT || QR, these two angles (∠PTR and ∠TRQ) are... wait, in the standard parallel lines cut by transversal, the angles that are on the same side of the transversal and between the parallel lines are consecutive interior angles (supplementary), but are these the ones?

Wait, let's draw two parallel horizontal lines, top and bottom. Draw a transversal that goes from the top line (at some point) to the bottom line (at some point), not perpendicular. The angle at the top line between the top line and the transversal (on the left side of the transversal) and the angle at the bottom line between the bottom line and the transversal (on the left side of the transversal) are consecutive interior angles, so they add to 180°.

In our diagram, is ∠PTR on the left side of transversal TR? Let's see: transversal TR goes from T (left part of top line) to R (right part of bottom line). At T, the angle ∠PTR is between PT (which is the top line going left) and TR (going down to R). So relative to transversal TR, at T, the angle between PT and TR is on the "left" side of TR (since PT is left of TR at T). At R, the angle ∠TRQ is between QR (bottom line going left) and TR (going up to T), so relative to transversal TR, at R, the angle between QR and TR is on the "left" side of TR (since QR is left of TR at R). Therefore, yes, these are the two consecutive interior angles on the same side of transversal TR, so they must be supplementary.

Yes! That makes sense. If you have the transversal going from top left to bottom right (like TR here: T is left of R horizontally? Wait, T is at x=7, R at x=10, so T is left of R on the bottom line? Wait, no, T is on the top line at x=7, R is on the bottom line at x=10, so horizontally, T is left of R (7 < 10). So transversal TR goes from a point left of the bottom line (T at x=7, top line) to a point right of T (R at x=10, bottom line), so it's a transversal going down to the right.

At the top intersection (T), the angle between the top line (going left) and the transversal (going down to the right) is ∠PTR = 2x° (this is the angle between the top line's left direction and the transversal).

At the bottom intersection (R), the angle between the bottom line (going left) and the transversal (going up to the left) is ∠TRQ = 128° (this is the angle between the bottom line's left direction and the transversal).

Since the two parallel lines are horizontal, and the transversal is going down to the right, the angles on the left side of the transversal at both intersections (the angles between the leftward direction of the parallel lines and the transversal) should be supplementary because they're consecutive interior angles.

Wait, maybe a better way: when two parallel lines are cut by a transversal, the alternate interior angles are equal, but here we have two angles on the same side, so consecutive interior.

Wait, let's use a different transversal to get a clear relation. Let's take the transversal that's the line QR? No, QR is one of the parallel lines.

Wait, another idea: the top line PT is a straight line, so the angles at P and T along PT... Wait, no, PT is a straight line, so the angles on one side of PT sum to 180°, but we have angles at P and T with respect to the other sides.

Wait, let's go back to the quadrilateral angle sum, which gave us y = 232 - 3x, so if we can find x, we're done. How do we find x?

Let's consider the transversal PQ with the parallel lines PT and QR.

At point P (on PT), the angle between PT and PQ is ∠QPT = x° (this is the angle inside the trapezoid, between PT (going right) and PQ (going down to Q))

At point Q (on QR), the angle between QR and PQ is ∠PQR = y° (inside the trapezoid, between QR (going right) and PQ (going up to P))

Since PT || QR, and PQ is a transversal, the consecutive interior angles here should be supplementary. Let's confirm the positions:

- PT is the top line (y=10), QR is the bottom line (y=0), parallel.
- Transversal PQ goes from P (top line, x=-7) to Q (bottom line, x=0), so it's going down to the right.
- At P (top line), the angle between PT (which is horizontal right from P) and PQ (which is down to the right from P) is x° (this is the angle between the top line's right direction and the transversal).
- At Q (bottom line), the angle between QR (which is horizontal right from Q) and PQ (which is up to the left from Q) is y° (this is the angle between the bottom line's right direction and the transversal).

Wait a second! In this case, the angles at P and Q are on opposite sides of the transversal PQ. At P, it's the angle above the transversal (since the trapezoid is below PT), and at Q, it's the angle below the transversal (since the trapezoid is above QR). Wait, maybe they are alternate interior angles?

Alternate interior angles are equal when lines are parallel. Let's see: if two parallel lines are cut by a transversal, the alternate interior angles are equal.

For transversal PQ cutting parallel lines PT and QR:

- Interior angles (between the parallel lines) are the angles inside the region between PT and QR.
- At P (on PT), the interior angle relative to transversal PQ is the angle between PT and PQ that's between PT and QR, which is ∠QPT = x° (since QR is below PT, this angle is below PT, so between PT and QR)
- At Q (on QR), the interior angle relative to transversal PQ is the angle between QR and PQ that's between PT and QR, which is ∠PQR = y° (since PT is above QR, this angle is above QR, so between PT and QR)

Yes! These are the alternate interior angles formed by transversal PQ and the parallel lines PT, QR. Therefore, by the alternate interior angles theorem, they should be equal.

Wait, hold on! Alternate interior angles are equal when the lines are parallel. Let's recall: if two parallel lines are cut by a transversal, then alternate interior angles are congruent.

In this case, the two parallel lines are PT and QR, transversal is PQ. The alternate interior angles would be the angles that are on opposite sides of the transversal and inside the two parallel lines.

At P: angle between PT (top line) and PQ (transversal) that's on the side towards QR (the bottom line) – that's ∠QPT = x° (since from P, PQ goes down to Q, which is on QR, so yes, towards QR)
At Q: angle between QR (bottom line) and PQ (transversal) that's on the side towards PT (the top line) – that's ∠PQR = y° (from Q, PQ goes up to P, which is on PT, so towards PT)

These two angles are on opposite sides of transversal PQ (one on the "lower" side of PQ at P, one on the "upper" side of PQ at Q) and both are between the two parallel lines, so they are alternate interior angles. Therefore, they must be equal!

Oh! This is probably the key relation I missed earlier by confusing consecutive vs alternate. Let's verify with the theorem:

Alternate interior angles: When two parallel lines are cut by a transversal, the angles that are inside the two parallel lines and on opposite sides of the transversal are congruent.

Yes! So in our case, the two angles (x° at P and y° at Q) are inside the parallel lines (between PT and QR), on opposite sides of the transversal PQ, so they are alternate interior angles ⇒ x = y.

Wait, but hold on, in the quadrilateral angle sum, we had y = 232 - 3x, so if x = y, then x = 232 - 3x ⇒ 4x = 232 ⇒ x = 58, so y = 58. But wait, let's check if the other transversal gives a consistent result, because we need to make sure we didn't mix up angles.

Wait, but let's check the other transversal TR to see if it gives the same or another relation.

For transversal TR cutting parallel lines PT and QR:

- At T (on PT), the angle between PT and TR that's inside the parallel lines (between PT and QR) is ∠PTR = 2x° (this is the angle at T between PT (top line) and TR (transversal), towards QR)
- At R (on QR), the angle between QR and TR that's inside the parallel lines (between PT and QR) is ∠TRQ = 128° (angle at R between QR (bottom line) and TR (transversal), towards PT)

Are these alternate interior angles or consecutive interior angles?

Alternate interior angles would be on opposite sides of the transversal. At T, the angle is on the side towards QR (which is below PT), at R, the angle is on the side towards PT (which is above QR). Let's see the sides of transversal TR:

Transversal TR goes from T (top line) to R (bottom line). At T, the angle ∠PTR is between PT (left along top line) and TR (down to R), so relative to TR, this angle is on the "left" side of TR. At R, the angle ∠TRQ is between QR (left along bottom line) and TR (up to T), so relative to TR, this angle is on the "left" side of TR as well. Therefore, they are on the same side of the transversal, so they are consecutive interior angles, hence supplementary.

Yes! That's the key. For transversal TR:

- Angles at T and R (both inside the parallel lines) are on the same side of transversal TR ⇒ consecutive interior angles ⇒ supplementary.

So that gives us: ∠PTR + ∠TRQ = 180°

We know ∠PTR = 2x°, ∠TRQ = 128°, so:

2x + 128 = 180 ⇒ 2x = 180 - 128 = 52 ⇒ x = 26

Oh! That's straightforward! Why did I overcomplicate with the quadrilateral first? Let's see if this makes sense.

Wait, let's confirm this consecutive interior angles for transversal TR.

Two parallel lines: PT (top) and QR (bottom), parallel.

Transversal: TR (connects T on top to R on bottom).

The two angles formed at the intersections that are between the parallel lines (i.e., inside the trapezoid) and on the same side of the transversal are ∠PTR (at T) and ∠TRQ (at R).

In the standard definition, consecutive interior angles are the two angles that are between the two parallel lines and on the same side of the transversal. Yes, that's the definition. So if you have two parallel lines cut by a transversal, the four angles formed are: two pairs of vertical angles, and the angles that are inside the parallel lines are the two pairs of consecutive interior angles (each pair summing to 180°).

So for transversal TR:

- At T: two angles formed with PT: one is ∠PTR = 2x° (inside the trapezoid, between PT and QR), the other is the angle outside the trapezoid
- At R: two angles formed with QR: one is ∠TRQ = 128° (inside the trapezoid, between PT and QR), the other is the angle outside the trapezoid

The two inside angles (the ones we care about for the trapezoid) are on the same side of transversal TR (both to the left of TR, as we thought earlier), so they are consecutive interior angles ⇒ supplementary.

Therefore, 2x + 128 = 180 ⇒ x = (180 - 128)/2 = 52/2 = 26. Perfect, that's a clear equation.

Now, why did I doubt this earlier? Let's make sure we didn't misidentify the angles.

The problem says: label("$2x^{\circ}$",(7,10),SW); (7,10) is point T, SW is southwest of T, so below and to the left of T. The angle at T that's below and to the left of T is the angle between the top line (going left from T, towards P) and the line TR (going down to R). Yes, that's the angle inside the trapezoid at T, between PT and TR, which is ∠PTR = 2x°.

The problem says: label("$128^{\circ}$",(10,0),NE); (10,0) is point R, NE is northeast of R, so above and to the left of R. The angle at R that's above and to the left of R is the angle between the bottom line (going left from R, towards Q) and the line TR (going up to T). Yes, that's the angle inside the trapezoid at R, between QR and TR, which is ∠TRQ = 128°.

Since PT || QR (given), and TR is a transversal, the consecutive interior angles ∠PTR and ∠TRQ must sum to 180°. Wait, but hold on! Wait a second, in some configurations, consecutive interior angles are supplementary, but is this the correct pair?

Let's take a simple case: two horizontal parallel lines, top and bottom. A transversal that goes from the top line at the left to the bottom line at the right (like TR here: T is left of R horizontally? Wait, T is at x=7, R at x=10, so T is left of R on the horizontal axis, yes, so transversal goes from top line (left) to bottom line (right), so it's a "rightward" transversal.

At the top intersection (T), the angle between the top line (going left) and the transversal (going right-down) is, say, α.

At the bottom intersection (R), the angle between the bottom line (going right) and the transversal (going left-up) is, say, β.

Wait, no, in our diagram, at R, the bottom line is QR going left (towards Q), not right. Q is at x=0, R at x=10, so QR is from Q(0,0) to R(10,0), so at R, the direction along QR is towards Q, which is left.

Similarly, at T, PT is from P(-7,10) to T(7,10), so at T, the direction along PT is towards P, which is left.

So both at T and R, the directions along the parallel lines are left (towards the interior of the trapezoid, since the trapezoid is to the left of the top base? Wait, no, the trapezoid has vertices Q, P, T, R, so it's a four-sided figure with the left side PQ and right side TR.

But maybe instead of getting bogged down in directions, let's use the fact that we have a straight line PT, so the angles at T along PT... Wait, no, PT is a straight line, but we have angles at P and T with respect to the other sides.

Wait, but here's a concrete way: let's draw the diagram step by step as per the asy code to visualize.

- Draw horizontal line from (0,0) to (10,0) with arrow (so QR is from Q(0,0) to R(10,0), bottom line)
- Draw another horizontal line from (10,0) to (20,0) (not important)
- Draw polygonal path from Q(0,0) up to P(-7,10) [left-up], then to T(7,10) [right along horizontal], then down to R(10,0) [right-down]
- Draw a horizontal line segment from (-5,10) to (7,10) with arrow (so this is part of PT, extending from P(-7,10) to T(7,10) and beyond to the right)

Now, the angle labels:

- "x°" is at (-6,10) SE: (-6,10) is on the horizontal line PT (y=10), 1 unit right of P(-7,10). SE from there is down and right, so the label is placed below and to the right of (-6,10), which is the angle at P between PT (going right) and PQ (going down to Q). So that angle is ∠QPT = x°, as we had.

- "2x°" is at (7,10) SW: (7,10) is T, SW from T is down and left, so the label is placed below and to the left of T, which is the angle at T between PT (going left) and TR (going down to R). So that angle is ∠PTR = 2x°, correct.

- "128°" is at (10,0) NE: (10,0) is R, NE from R is up and left, so the label is placed above and to the left of R, which is the angle at R between QR (going left) and RT (going up to T). So that angle is ∠TRQ = 128°, correct.

Now, let's consider the straight line PT: it's a straight line, so the angles on one side of PT should sum to 180°, but we have angles at P and T with respect to other lines.

Wait, but here's a better idea: since PT || QR, the angle between PT and TR at T should be equal to the angle between QR and TR at R if they are alternate interior angles, but no—wait, let's use the concept of corresponding angles.

Corresponding angles: when two parallel lines are cut by a transversal, corresponding angles are equal.

For transversal TR:

- At T (on PT), the angle above the transversal (if we consider PT as the top line) would correspond to the angle at R (on QR) above the transversal.
- But in our case, the angle at T inside the trapezoid is ∠PTR = 2x° (between PT and TR, below PT), and the angle at R inside the trapezoid is ∠TRQ = 128° (between QR and TR, above QR).

Wait, maybe it's easier to use the fact that the sum of angles on a straight line is 180°.

Wait, no—let's go back to the transversal TR and the parallel lines. Let's imagine extending the lines if necessary.

Since PT || QR, the angle that TR makes with PT at T should be equal to the angle that TR makes with QR at R, but only if they are corresponding angles.

Let's define the angle at T between PT and TR as 2x°, and since PT || QR, the corresponding angle at R (on the same side of TR) should be equal to 2x°. Wait, but the angle at R is given as 128°, so is 2x° equal to 128°? No, that can't be, because then x=64, but let's see.

Wait, no—corresponding angles are equal. Let's be precise:

- Line 1: PT (top, parallel to QR)
- Line 2: QR (bottom, parallel to PT)
- Transversal: TR

Corresponding angles would be:

- At T (on Line 1): angle between Line 1 (PT) and Transversal (TR) on the "upper" side of Transversal TR
- At R (on Line 2): angle between Line 2 (QR) and Transversal (TR) on the "upper" side of Transversal TR

But in our diagram, the angle at T on the "upper" side of TR would be outside the trapezoid (since the trapezoid is below TR), and the angle at R on the "upper" side of TR would be outside the trapezoid too. We have the angles inside the trapezoid, so they are not corresponding angles.

The angles inside the trapezoid at T and R are consecutive interior angles, so they must sum to 180°. Let's test with a known example.

Suppose we have two horizontal parallel lines, top and bottom. A transversal that goes from top line at x=0 to bottom line at x=1 (so it's a line with positive slope). At the top line (x=0), the angle between the top line (horizontal) and the transversal (going down to the right) that's inside the region between the lines is, say, 30°. At the bottom line (x=1), the angle between the bottom line (horizontal) and the transversal (going up to the left) that's inside the region between the lines is 150° (since 30 + 150 = 180). Yes! That's the classic example: consecutive interior angles sum to 180°.

In this example, the two angles inside the parallel lines (the region between them) on the same side of the transversal sum to 180°.

In our problem, the "region between the parallel lines" is the trapezoid (the area bounded by the two parallel sides and the two legs), so the angles at T and R inside the trapezoid are exactly the two consecutive interior angles for transversal TR, hence they must sum to 180°.

Therefore, ∠PTR + ∠TRQ = 180° ⇒ 2x + 128 = 180 ⇒ 2x = 52 ⇒ x = 26.

Great, so now we have x = 26°. Now we need to find ∠PQR.

How do we find ∠PQR? Let's use the other transversal, PQ, with the parallel lines PT and QR.

Transversal PQ cuts parallel lines PT and QR at P and Q, respectively.

The angles inside the trapezoid at P and Q are:

- At P: ∠QPT = x° (between PT and PQ, inside the trapezoid)
- At Q: ∠PQR = ? (between QR and PQ, inside the trapezoid)

Since PT || QR, and PQ is a transversal, what are these angles?

In the same example as above, for transversal PQ, the two angles inside the parallel lines (the trapezoid) would be:

- At P: angle between PT (top line) and PQ (transversal) inside the region ⇒ x°
- At Q: angle between QR (bottom line) and PQ (transversal) inside the region ⇒ ∠PQR

Are these consecutive interior angles or alternate interior angles?

In the example with transversal going down to the right, the angles inside the parallel lines at the two intersections are on opposite sides of the transversal, so they are alternate interior angles, hence equal.

Wait, in the example: top line at x=0, transversal to bottom line at x=1, angle at top (inside) is 30°, angle at bottom (inside) is 150° (consecutive interior, sum to 180°). But if the transversal is going up to the left, then the angles inside would be on opposite sides and equal.

Wait, let's get back to the diagram's coordinates to find the relationship.

At point P(-7,10): angle between PT (which is horizontal to the right, since T is at (7,10) right of P) and PQ (which is to Q(0,0), so right and down from P) is ∠QPT = x°. So this angle is below PT (since PQ goes down), so it's the angle between the top line (PT) and the leg PQ, on the bottom side of PT.

At point Q(0,0): angle between QR (which is horizontal to the right, since R is at (10,0) right of Q) and PQ (which is to P(-7,10), so left and up from Q) is ∠PQR. So this angle is above QR (since PQ goes up), so it's the angle between the bottom line (QR) and the leg PQ, on the top side of QR.

Since PT || QR, the angle below PT at P (x°) and the angle above QR at Q (∠PQR) are alternate interior angles with respect to transversal PQ. Why? Because they are on opposite sides of the transversal PQ and between the two parallel lines.

Yes! Alternate interior angles are equal when the lines are parallel. Let's confirm with the theorem:

If two parallel lines are cut by a transversal, then the alternate interior angles are congruent.

- Alternate interior angles: angles that are inside the two parallel lines and on opposite sides of the transversal.

In our case:

- The two parallel lines are PT and QR.
- The transversal is PQ.
- The angle at P (inside the parallel lines) is ∠QPT = x° (below PT, between PT and QR)
- The angle at Q (inside the parallel lines) is ∠PQR (above QR, between PT and QR)
- These two angles are on opposite sides of transversal PQ (one is "below" PQ at P, one is "above" PQ at Q) ⇒ alternate interior angles ⇒ congruent ⇒ ∠PQR = x°

Wait, but hold on! In the quadrilateral angle sum, we had y = 232 - 3x, where y = ∠PQR. If y = x, then x = 232 - 3x ⇒ 4x = 232 ⇒ x = 58, but we just found x = 26 from the other angle. Contradiction! So that means we misidentified which angles are alternate interior.

Ah! Here's the critical mistake: the angle at Q is not the alternate interior angle to the angle at P. Let's use the straight line at the bottom.

Wait, let's list all the angles around the points to make sure.

At point R(10,0): the line QR goes from Q(0,0) to R(10,0) (right along x-axis), and the line RT goes from R(10,0) to T(7,10) (left and up). So the two lines at R are QR (right) and RT (left-up), so the angle between them is 128° (given). The other angle at R (the one outside the trapezoid) would be 180° - 128° = 52°, since QR is a straight line (wait, no—QR is a segment from Q to R, but the line QR is infinite in both directions, so at point R, the straight line QR has a 180° angle, so the angle between RT and the extension of QR beyond R is 180° - 128° = 52°.

Similarly, at point T(7,10): the line PT goes from P(-7,10) to T(7,10) (right along y=10), so the straight line PT has 180° at T. The angle between PT (left) and TR (right-down) is 2x° (given), so the angle between PT (right) and TR (right-down) is 180° - 2x°.

Now, here's the key: since PT || QR, the angle that TR makes with PT at T (on the side towards QR) should be equal to the angle that TR makes with QR at R (on the side towards PT), but let's use the corresponding angles properly.

Let's consider the direction of the parallel lines: both are horizontal, so let's think in terms of slopes.

The angle that line TR makes with the horizontal line PT at point T is equal to the angle it makes with the horizontal line QR at point R, because PT || QR (corresponding angles).

Wait, the angle between a line and a horizontal line is the angle it makes with the x-axis.

Line TR has slope m = (0 - 10)/(10 - 7) = -10/3, so the angle θ it makes with the positive x-axis is arctan(-10/3), but the acute angle with the horizontal is arctan(10/3) ≈ 73.3°.

At point T (on PT, horizontal), the angle between PT (horizontal) and TR is the angle between the horizontal and TR, which is θ ≈ 73.3°.

At point R (on QR, horizontal), the angle between QR (horizontal) and TR is also θ ≈ 73.3°, because they're corresponding angles (same side of transversal, same direction of parallel lines).

But wait, in our diagram, at point T, the angle ∠PTR = 2x° is the angle between PT (which is the horizontal line, but we're taking the direction towards P, i.e., left) and TR (which is down to R). So if the angle between the horizontal (right) and TR is θ, then the angle between the horizontal (left) and TR is 180° - θ.

Similarly, at point R, the angle ∠TRQ = 128° is the angle between QR (which is the horizontal line, direction towards Q, i.e., left) and TR (which is up to T). So the angle between the horizontal (right) and TR at R is 180° - 128° = 52°, because QR is a straight line.

Ah! This is the confusion: the angle labels are measured in a specific direction, but we need to consider the angle between the line and the parallel line in the same orientation.

Let's use the fact that for parallel lines cut by a transversal, corresponding angles are equal. Let's define the "corresponding" angles based on the direction of the parallel lines.

Since PT || QR, and we have transversal TR, the corresponding angles would be:

- At T: the angle above transversal TR (if we consider PT as the top line)
- At R: the angle above transversal TR (on the bottom line)

But maybe it's simpler to use the straight line at the bottom and the transversal.

Wait, here's a foolproof method: let's find the measure of the angle at R on the other side of TR, then use the parallel lines.

At point R, the total angle around R is 360°, but we only care about the angles on the straight line QR.

Line QR is a straight line (the bottom base), so the angles on one side of QR sum to 180°. At point R, the line QR has two directions: towards Q (left) and towards the extension beyond R (right). The angle between QR (towards Q) and RT is 128° (given), so the angle between QR (towards extension beyond R) and RT is 180° - 128° = 52°.

Now, since PT || QR, the angle between PT and RT at T (on the side towards the extension of QR) should be equal to the angle between QR and RT at R (on the side towards the extension beyond R), because they are corresponding angles.

Yes! Corresponding angles: when two parallel lines are cut by a transversal, the angles that are in the same relative position at each intersection are equal.

- Let's take the "right" side of the transversal TR (the side where the extension of QR beyond R is).
- At R (on QR), the angle between QR (extension beyond R, i.e., right) and TR is 52° (as calculated: 180° - 128° = 52°)
- At T (on PT), the angle between PT (extension beyond T, i.e., right) and TR is the angle we need to find.

But in our diagram, at T, the angle between PT (towards P, left) and TR is 2x°, so the angle between PT (towards extension beyond T, right) and TR is 180° - 2x° (since PT is a straight line).

Since these two angles are corresponding angles (same side of transversal TR, same side of parallel lines), they must be equal:

180° - 2x° = 52° ⇒ 180 - 2x = 52 ⇒ 2x = 180 - 52 = 128 ⇒ x = 64

Wait, now we have a different x! This is confusing. Let's do this step by step with the straight line.

At point R:

- The line QR is straight (infinite line), so the angle between QR and RT on one side is 128°, so on the other side (the side opposite to the trapezoid) it's 180° - 128° = 52°.

At point T:

- The line PT is straight (infinite line), so the angle between PT and TR on one side is 2x°, so on the other side it's 180° - 2x°.

Since PT || QR, the angle on the "outside" of the trapezoid at T (180° - 2x°) should be equal to the angle on the "outside" of the trapezoid at R (52°), because they are corresponding angles (both on the side where the parallel lines extend outward from the trapezoid).

Yes! Corresponding angles are equal when lines are parallel. The "outside" angles at T and R with respect to transversal TR are corresponding angles, so they are equal.

Therefore:

180° - 2x° = 52° ⇒ 2x = 128 ⇒ x = 64

Wait, but why did we think they were supplementary before? Because we were looking at the "inside" angles, but the inside angles are consecutive interior, which are supplementary.

Let's clarify with a standard definition:

- When two parallel lines are cut by a transversal:
  - Corresponding angles: equal (same side of transversal, same side of parallel lines)
  - Alternate interior angles: equal (opposite sides of transversal, between parallel lines)
  - Consecutive interior angles: supplementary (same side of transversal, between parallel lines)

In our diagram, for transversal TR:

- The "between parallel lines" region is the trapezoid (the area between PT and QR).
- The "same side of transversal TR" for the consecutive interior angles: let's pick the side where the trapezoid is. Wait, maybe the safest way is to use the quadrilateral angle sum with the correct angle relations.

Let's go back to the quadrilateral QPTR (vertices in order Q, P, T, R). The sum of interior angles is 360°.

We have:

- At Q: ∠PQR = y (unknown)
- At P: ∠QPT = x (label at P, x°)
- At T: ∠PTR = 2x (label at T, 2x°)
- At R: ∠TRQ = 128 (label at R, 128°)

Sum: y + x + 2x + 128 = 360 ⇒ y + 3x = 232 ⇒ y = 232 - 3x (equation 1)

Now, we need another equation relating x and y.

The problem states PT || QR. Let's consider the line PT and line QR as parallel, so the angles formed by any transversal with them will have the relations above.

Let's take the transversal TR:

- At T: the angle between PT and TR is ∠PTR = 2x° (interior angle of quadrilateral)
- At R: the angle between QR and TR is ∠TRQ = 128° (interior angle of quadrilateral)

Since PT || QR, and TR is a transversal, the sum of the interior angles on the same side of the transversal is 180° (consecutive interior angles). Wait, but in the quadrilateral, are these the interior angles on the same side?

In a trapezoid, the two angles adjacent to a leg are supplementary. Yes! This is a key property of trapezoids: in a trapezoid with bases (parallel sides), each leg forms supplementary angles with the bases.

So for trapezoid QPTR with bases PT and QR (the parallel sides), the legs are PQ and TR.

- The leg TR connects base PT (at T) to base QR (at R), so the angles at T and R (adjacent to leg TR) should be supplementary.

Yes! That's a standard trapezoid property: in a trapezoid, the angles adjacent to each leg are supplementary.

Therefore, ∠PTR + ∠TRQ = 180°

This is the equation we need! Let's confirm with a trapezoid: if you have a trapezoid with two parallel sides, the angles next to the same leg add up to 180° because they are consecutive interior angles for the transversal leg and the parallel bases.

Yes! For example, in a right trapezoid, one leg is perpendicular to the bases, so the angles are 90° and 90°, which sum to 180°. In a non-right trapezoid, the angles adjacent to a leg are supplementary.

So applying this to our trapezoid:

- Leg TR has adjacent angles at T and R: ∠PTR (at T) and ∠TRQ (at R)
- Therefore, ∠PTR + ∠TRQ = 180°

We know ∠PTR = 2x°, ∠TRQ = 128°, so:

2x + 128 = 180 ⇒ 2x = 52 ⇒ x = 26

There we go! This is a standard trapezoid property that we can rely on, no confusion about directions. In any trapezoid (with exactly one pair of parallel sides), the angles adjacent to each non-parallel side (the legs) are supplementary.

So that gives us x = 26°.

Now, we need to find ∠PQR, which is the angle at Q (adjacent to leg PQ).

Let's apply the same trapezoid property to the other leg, PQ.

- Leg PQ has adjacent angles at P and Q: ∠QPT (at P) and ∠PQR (at Q)
- Therefore, ∠QPT + ∠PQR = 180°

Yes! This is the key. In trapezoid QPTR with bases PT and QR, the legs are PQ and TR. For leg PQ, the two angles at its endpoints (P and Q) are supplementary.

We have ∠QPT = x° (given by the label at P), and ∠PQR = y° (what we need), so:

x + y = 180°

Wait, hold on! Earlier we had the quadrilateral angle sum giving y = 232 - 3x, but now this says y = 180 - x. Let's check which one is correct.

Wait, no—wait, in the trapezoid, are the angles adjacent to the leg the ones we think?

Let's define the trapezoid properly: a trapezoid has exactly one pair of parallel sides (the bases). Here, PT || QR, so bases are PT and QR. The legs are the non-parallel sides: PQ and TR.

At each base, there are two angles:

- Base PT (top base): angles at P and T (the two endpoints of the top base)
- Base QR (bottom base): angles at Q and R (the two endpoints of the bottom base)

In a trapezoid, the angles adjacent to each leg are supplementary. A leg connects a top base endpoint to a bottom base endpoint.

- Leg PQ connects top base endpoint P to bottom base endpoint Q ⇒ angles at P (top base) and Q (bottom base) are adjacent to leg PQ ⇒ they are supplementary
- Leg TR connects top base endpoint T to bottom base endpoint R ⇒ angles at T (top base) and R (bottom base) are adjacent to leg TR ⇒ they are supplementary

Yes! This is the correct trapezoid property. So for leg PQ: angles at P and Q (one on each base) are supplementary. For leg TR: angles at T and R (one on each base) are supplementary.

Let's verify with the angle labels:

- Angle at P (top base): this is the angle between the top base PT and leg PQ ⇒ ∠QPT = x° (correct, as labeled)
- Angle at Q (bottom base): this is the angle between the bottom base QR and leg PQ ⇒ ∠PQR = y° (this is exactly the angle we need to find)

Therefore, since they are adjacent to leg PQ, they are supplementary: x + y = 180° (equation 2)

Similarly:

- Angle at T (top base): angle between top base PT and leg TR ⇒ ∠PTR = 2x° (labeled)
- Angle at R (bottom base): angle between bottom base QR and leg TR ⇒ ∠TRQ = 128° (labeled)

These are adjacent to leg TR, so they are supplementary: 2x + 128 = 180° (equation 3)

Ah! Now this makes sense. Equation 3 gives us x = 26°, then equation 2 gives us y = 180° - x = 180 - 26 = 154°.

Wait, but hold on, let's make sure we didn't mix up the angles at the bases.

In a trapezoid, the base angles are the angles at each base. For base PT (top), the base angles are at P and T; for base QR (bottom), the base angles are at Q and R.

The property is: consecutive angles between the bases (i.e., angles adjacent to the same leg) are supplementary.

So for leg PQ (connecting top base to bottom base), the two base angles it "sees" are the top base angle at P and the bottom base angle at Q ⇒ they are supplementary.

Yes, that's the standard trapezoid angle property. For example, in an isosceles trapezoid, base angles are equal, and adjacent angles to a leg are supplementary (so each base has two equal angles, and the two bases have supplementary angles).

Let's test with equation 3 first, which is straightforward.

Equation 3: angles at T and R (adjacent to leg TR) are supplementary because PT || QR.

We have angle at T (top base, adjacent to TR) = 2x°, angle at R (bottom base, adjacent to TR) = 128°, so 2x + 128 = 180 ⇒ x = 26°. This seems solid because it's a direct application of consecutive interior angles (which are supplementary) for the transversal TR and parallel lines PT, QR.

Now, equation 2: angles at P and Q (adjacent to leg PQ) are supplementary.

Angle at P (top base, adjacent to PQ) = x° (given), angle at Q (bottom base, adjacent to PQ) = ∠PQR = y° (what we need), so x + y = 180° ⇒ y = 180 - 26 = 154°.

But wait, let's check with the quadrilateral angle sum to be sure.

Quadrilateral angle sum: y + x + 2x + 128 = 360 ⇒ y + 3x = 232

If y = 154 and x = 26, then 154 + 3*26 = 154 + 78 = 232. Perfect! It matches the quadrilateral angle sum.

Earlier, I mistakenly thought the angles at P and Q were alternate interior, but in reality, for the trapezoid, they are consecutive interior angles with respect to the transversal PQ and the parallel lines, hence supplementary.

Wait, no—consecutive interior angles are supplementary, and in the trapezoid, the angles adjacent to a leg are consecutive interior angles for the transversal leg and the parallel bases, so they must be supplementary. Yes, that's consistent.

Let's recap to make sure we didn't skip any steps:

1. Identify the trapezoid: QPTR with PT || QR (given), so it's a trapezoid with bases PT and QR.
2. In a trapezoid, angles adjacent to each leg are supplementary (this is a theorem for trapezoids, derived from parallel lines and transversals).
3. Leg TR connects T (on top base PT) to R (on bottom base QR), so the angles at T and R (adjacent to leg TR) are supplementary: ∠PTR + ∠TRQ = 180°.
4. From the diagram, ∠PTR = 2x° (labeled at T) and ∠TRQ = 128° (labeled at R), so 2x + 128 = 180 ⇒ x = 26°.
5. Leg PQ connects P (on top base PT) to Q (on bottom base QR), so the angles at P and Q (adjacent to leg PQ) are supplementary: ∠QPT + ∠PQR = 180°.
6. From the diagram, ∠QPT = x° (labeled at P), so x + ∠PQR = 180° ⇒ ∠PQR = 180° - x = 180 - 26 = 154°.

The quadrilateral angle sum confirms this: 154 + 26 + 52 + 128 = 154 + 26 = 180; 52 + 128 = 180; 180 + 180 = 360. Perfect, sums to 360°.

Earlier confusion was about whether the angles were consecutive or alternate interior, but by using the trapezoid's angle property (which is a direct consequence of the parallel lines and transversals), we can be confident.

Let's just visualize the angles to ensure they make sense:

- At R, the angle is 128°, which is obtuse, so the angle outside the trapezoid at R is 52° (180 - 128).
- Since PT || QR, the angle outside at T should equal the angle outside at R (corresponding angles), so the angle at T outside the trapezoid is 52°.
- The angle at T inside the trapezoid is 2x = 52°? Wait, no—wait, if the angle outside at T is 52°, then the angle inside at T is 180 - 52 = 128°? Wait, no, let's not confuse inside/outside.

Wait, no—using the trapezoid property we have:

- Inside the trapezoid at T: 2x°
- Inside the trapezoid at R: 128°
- These two are supplementary (from the trapezoid leg property), so 2x + 128 = 180 ⇒ x = 26, so inside at T is 52°, inside at R is 128°.

That makes sense: 52° + 128° = 180°, so they're supplementary, which is correct for consecutive interior angles.

Then inside at P: x = 26°, inside at Q: 180 - 26 = 154°, so 26 + 154 = 180°, supplementary, correct.

Quadrilateral angles: 26 (P) + 52 (T) + 128 (R) + 154 (Q) = 26+52=78; 128+154=282; 78+282=360. Perfect, adds up.

The key was recognizing the trapezoid and applying the angle property for trapezoids (or directly the consecutive interior angles for the transversal with parallel lines).

I think the confusion earlier was about which angles are which, but by systematically listing the angles with their vertices and using the quadrilateral angle sum as a check, we can be sure.

So to summarize the steps clearly:

1. The diagram shows a trapezoid with bases PT and QR (given PT || QR).
2. The angle at T (between PT and TR) is labeled 2x°, and the angle at R (between QR and TR) is labeled 128°.
3. Since PT || QR and TR is a transversal, the angles at T and R (adjacent to leg TR) are consecutive interior angles and thus supplementary: 2x + 128 = 180 ⇒ x = 26.
4. The angle at P (between PT and PQ) is labeled x° = 26°, and the angle at Q (between QR and PQ) is ∠PQR, which is adjacent to leg PQ with the angle at P, so they are supplementary: ∠PQR + x = 180 ⇒ ∠PQR = 154.

Yes, this all checks out. The quadrilateral angle sum confirms the values, so we can be confident.

I think the initial hesitation was due to misidentifying the angles, but by breaking it down step by step and verifying with multiple methods (trapezoid property, consecutive interior angles, quadrilateral angle sum), we arrive at the answer.

**Final Answer**
\boxed{154}
</think>

To determine the measure of $\angle PQR$, we begin by analyzing the diagram and identifying the key geometric relationships.

---

### **Step 1: Understand the Diagram**

From the Asymptote code and the given labels:

- Points:
  - $Q = (0, 0)$
  - $R = (10, 0)$
  - $P = (-7, 10)$
  - $T = (7, 10)$

- The segment $PT$ is horizontal from $P$ to $T$, so it's parallel to the segment $QR$ (also horizontal), as stated in the problem: **$PT \parallel QR$**.

This makes quadrilateral $QPTR$ a **trapezoid**, with bases $PT$ and $QR$ being the two parallel sides.

---

### **Step 2: Identify Known Angles**

We are given:

- $\angle PTR = 2x^\circ$ at point $T$
- $\angle TRQ = 128^\circ$ at point $R$
- $\angle QPT = x^\circ$ at point $P$

We want to find $\angle PQR$ at point $Q$.

---

### **Step 3: Use Trapezoid Angle Properties**

In any trapezoid with one pair of parallel sides (the bases), the **angles adjacent to each leg are supplementary**. This is because the legs act as transversals cutting the parallel bases.

#### For leg $TR$:
- Angles at $T$ and $R$ are adjacent to leg $TR$
- So, $\angle PTR + \angle TRQ = 180^\circ$

Substitute known values:

$$
2x + 128 = 180 \Rightarrow 2x = 52 \Rightarrow x = 26
$$

So, $\angle QPT = x = 26^\circ$

#### For leg $PQ$:
- Angles at $P$ and $Q$ are adjacent to leg $PQ$
- So, $\angle QPT + \angle PQR = 180^\circ$

Substitute known value:

$$
26 + \angle PQR = 180 \Rightarrow \angle PQR = 154^\circ
$$

---

### **Step 4: Verify with Quadrilateral Angle Sum**

The sum of interior angles in a quadrilateral is always $360^\circ$. Let’s check:

- $\angle QPT = 26^\circ$
- $\angle PTR = 2x = 52^\circ$
- $\angle TRQ = 128^\circ$
- $\angle PQR = 154^\circ$

$$
26 + 52 + 128 + 154 = 360
$$

✅ This confirms our calculation is consistent.

---

### ✅ Final Answer

$$
\boxed{154}
$$
```

