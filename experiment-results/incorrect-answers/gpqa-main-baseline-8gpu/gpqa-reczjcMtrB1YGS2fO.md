# gpqa-reczjcMtrB1YGS2fO

Run: gpqa-main-baseline-8gpu; arm: baseline.

Expected: C
Model answer: B
Scoring outcome: wrong extracted answer; answer source: after_thinking_end.

## Question

Consider an aperture, which shapes like a N-sided polygon. All the apothems are of the same length a. When a monochromatic light (of wavelength \lambda), travelling along z-axis, falls vertically on this aperture, it creates a series of intensity maxima and minima in the far field region. What is the angular distance between the first two minima when N is infinitely large ? Assume that the related angles are small so that tan theta = theta approximation can be taken.

(A) 1.220 \lambda /a 
(B) 0.610 \lambda / a
(C) 0.506 \lambda / a
(D) 0.500 \lambda / a

## Final response

```text


To determine the **angular distance between the first two minima** in the far field diffraction pattern of a monochromatic light wave incident on a **polygonal aperture** with **infinitely many sides**, we must first understand the physical setup and the limiting behavior as $ N \to \infty $.

---

### Step 1: Understanding the Aperture Shape

The problem describes an **N-sided polygon** with **all apothems of length $ a $**. The **apothem** is the perpendicular distance from the center of a regular polygon to the midpoint of one of its sides.

For a regular polygon with $ N $ sides, the **apothem** $ a $ and the **radius** $ R $ (distance from center to a vertex) are related by:

$$
a = R \cos\left(\frac{\pi}{N}\right)
$$

As $ N \to \infty $, $ \frac{\pi}{N} \to 0 $, so $ \cos\left(\frac{\pi}{N}\right) \to 1 $, and thus:

$$
R \to a
$$

This means that **as $ N \to \infty $**, the polygon becomes a **circle of radius $ a $**.

---

### Step 2: Diffraction Pattern of a Circular Aperture

When monochromatic light of wavelength $ \lambda $ falls on a circular aperture of **radius $ R = a $**, the far-field diffraction pattern is governed by the **Bessel function of the first kind** $ J_1(x) $, where:

$$
x = \frac{\pi R \sin\theta}{\lambda}
$$

The **first minimum** in the diffraction pattern occurs when $ J_1(x) = 0 $, which happens at:

$$
x = \frac{\pi R \sin\theta}{\lambda} = 3.8317 \quad \Rightarrow \quad \sin\theta = \frac{3.8317 \lambda}{\pi R}
$$

For **small angles**, $ \sin\theta \approx \theta $, so:

$$
\theta \approx \frac{3.8317 \lambda}{\pi R}
$$

Substituting $ R = a $, we get:

$$
\theta_1 \approx \frac{3.8317}{\pi} \cdot \frac{\lambda}{a} \approx 1.220 \cdot \frac{\lambda}{a}
$$

This is the **angle to the first minimum** from the center.

The **second minimum** occurs at the **next zero** of $ J_1(x) $, which is at $ x \approx 7.0156 $. So:

$$
\theta_2 \approx \frac{7.0156}{\pi} \cdot \frac{\lambda}{a} \approx 2.234 \cdot \frac{\lambda}{a}
$$

Therefore, the **angular distance between the first and second minima** is:

$$
\Delta\theta = \theta_2 - \theta_1 \approx (2.234 - 1.220) \cdot \frac{\lambda}{a} = 1.014 \cdot \frac{\lambda}{a}
$$

Wait — this seems inconsistent with the standard formula. Let's reconcile this with the **standard diffraction formula** used in optics.

---

### Step 3: Standard Diffraction Formula for Circular Apertures

In most optics contexts, the **first minimum** in the diffraction pattern of a **circular aperture of diameter $ D $** occurs at:

$$
\sin\theta = \frac{1.22 \lambda}{D}
$$

For **small angles**, $ \sin\theta \approx \theta $, so:

$$
\theta_1 \approx \frac{1.22 \lambda}{D}
$$

The **second minimum** occurs at:

$$
\theta_2 \approx \frac{2.44 \lambda}{D}
$$

So the **angular distance between the first and second minima** is:

$$
\Delta\theta = \theta_2 - \theta_1 = \frac{2.44 \lambda - 1.22 \lambda}{D} = \frac{1.22 \lambda}{D}
$$

Now, in our case, the **diameter** $ D $ of the aperture is $ 2a $ (since the radius is $ a $), so:

$$
\Delta\theta = \frac{1.22 \lambda}{2a} = 0.61 \cdot \frac{\lambda}{a}
$$

---

### Step 4: Final Answer

This matches **Option (B)**: $ 0.610 \lambda / a $

The key insight is that the **angular distance between the first two minima** (on the same side of the central maximum) is **not** the full angular width of the central peak, but the **difference** between the second and first minima, which is $ \frac{1.22 \lambda}{D} $, and with $ D = 2a $, this becomes $ 0.61 \lambda / a $.

---

### Final Answer

Final answer: (B)
```

## Full generated reasoning and answer

```text
Okay, let's try to figure out this problem step by step. Hmm, the question is about an aperture that's a polygon with N sides, all apothems of length a. When monochromatic light with wavelength λ hits it along the z-axis, we need to find the angular distance between the first two minima in the far field when N is infinitely large. And they mention small angles so we can use tanθ ≈ θ.

First, I remember that for diffraction patterns, especially from circular apertures, the first minimum occurs at an angle θ where sinθ = 1.22 λ / D, where D is the diameter. But here, the aperture is a polygon with infinitely many sides, which should approximate a circle. Wait, as N becomes very large, a polygon with N sides approaches a circle. The apothem a is the distance from the center to the midpoint of a side, right?

For a regular polygon with N sides, the apothem a is related to the radius R of the circumscribed circle (the distance from center to a vertex) by a = R cos(π/N). As N becomes very large, π/N becomes very small, so cos(π/N) ≈ 1 - (π²)/(2N²), which approaches 1. So R ≈ a for large N. Wait, but if N is infinitely large, then the polygon becomes a circle with radius R = a? Hmm, maybe not exactly. Wait, the apothem is the distance from the center to the side, so in a circle, the apothem would be the radius? Wait, no. Wait, in a circle, the apothem is the radius because all sides (which are infinitesimal) are at distance R from the center. Wait, maybe I need to clarify.

Let me recall: For a regular polygon with N sides, the apothem (a) is the distance from the center to a side, and the radius (R) is the distance from center to a vertex. The relationship is a = R cos(π/N). So if N is very large, then π/N is very small, so cos(π/N) ≈ 1 - (π²)/(2N²), so a ≈ R. So as N → ∞, a approaches R. Therefore, the polygon with N sides becomes a circle with radius R = a.

Wait, but in the problem statement, it says "all the apothems are of the same length a". So for a regular polygon, all apothems are equal, so that's correct. So when N is infinitely large, the aperture becomes a circle with radius a. Wait, but in the standard diffraction formula for a circular aperture, the first minimum is at sinθ = 1.22 λ / D, where D is the diameter. Wait, but here, the radius would be a, so diameter D = 2a. Hmm.

Wait, but maybe the problem is using "apothem" differently? Wait, no, apothem is standard for regular polygons. Let me confirm: Apothem is the distance from center to the midpoint of a side. So for a regular polygon, the apothem a = R cos(π/N), where R is the radius (distance from center to vertex). So for large N, a ≈ R. So as N approaches infinity, the polygon becomes a circle with radius R = a.

So the aperture is a circle of radius a. Then the diffraction pattern from a circular aperture has its first minimum at sinθ = 1.22 λ / (2a), since diameter D = 2a. Wait, but hold on: in the standard formula, the first minimum is at sinθ = 1.22 λ / D, where D is the diameter. So if D = 2a, then sinθ = 1.22 λ / (2a) ≈ 1.22 λ / (2a) = 0.61 λ / a. But the question asks for the angular distance between the first two minima. Wait, wait, for a circular aperture, there's only one set of minima? Wait, no, in the far field, the diffraction pattern has a central maximum with minima at angles θ where sinθ = 1.22 λ / D, 2.44 λ / D, etc. Wait, no, actually, the first minimum is at 1.22 λ / D, the next at ~2.44 λ / D, so the angular distance between first and second minima would be (2.44 - 1.22) λ / D = 1.22 λ / D. Wait, but the problem says "the angular distance between the first two minima". Hmm, but in the circular aperture case, the first minimum is the first one on either side of the center? Wait, no, the diffraction pattern for a circular aperture has a central peak, then the first minimum at angle θ, then a secondary peak, then second minimum, etc. So the first minimum (closest to the center) is at θ = 1.22 λ / D, and the next minimum (the second one) is at ~2.44 λ / D. So the angular separation between the first and second minima would be 1.22 λ / D. Wait, but the problem says "the angular distance between the first two minima". Hmm.

Wait, but in this problem, the aperture is a polygon with N sides, N approaching infinity. So it's a circular aperture. The standard formula for the first minimum in circular aperture diffraction is sinθ = 1.22 λ / D, where D is the diameter. Wait, but in some references, it's written as sinθ = 1.22 λ / (2R), where R is the radius. Let me get this straight.

Let me recall the formula. The angular radius of the first minimum for a circular aperture of radius R is given by θ = 1.22 λ / (2R). Wait, no. Wait, the diffraction pattern from a circular aperture has the first minimum at an angle θ where sinθ = 1.22 λ / D, D being the diameter. So if the aperture has radius R, then D = 2R. So sinθ = 1.22 λ / (2R). Then, for small angles, sinθ ≈ θ, so θ ≈ 1.22 λ / (2R). But in this problem, the apothem a is given. Wait, earlier we thought that for large N, the polygon becomes a circle with radius R ≈ a. Wait, but according to the polygon apothem definition, a = R cos(π/N), so R = a / cos(π/N). As N approaches infinity, cos(π/N) approaches 1, so R approaches a. So the radius R of the circle is a.

Wait, so if R = a, then θ ≈ 1.22 λ / (2R) = 1.22 λ / (2a) = 0.61 λ / a. But the problem says "the angular distance between the first two minima". Wait, in the circular aperture diffraction pattern, the first minimum is at θ = 0.61 λ / a (if R = a), and the next minimum is at θ ≈ 1.22 λ / a. Wait, no. Wait, actually, the formula is that the first minimum occurs at sinθ = 1.22 λ / D, so if D is the diameter. If the aperture has radius R, then D = 2R. So sinθ = 1.22 λ / (2R). So θ ≈ 1.22 λ / (2R). So if R = a (since as N→∞, R approaches a), then θ ≈ 1.22 λ / (2a) = 0.61 λ / a. Then the angular distance between the first minimum and the second minimum would be the difference between the second and first minimum angles. Wait, but in the diffraction pattern of a circular aperture, the first minimum is at θ1 = 1.22 λ / D, the second minimum at θ2 ≈ 2.44 λ / D. So the angular distance between them is θ2 - θ1 = 1.22 λ / D. But here D = 2a, so 1.22 λ / (2a) = 0.61 λ / a. Wait, but the problem states "the angular distance between the first two minima". Hmm, so if the first minimum is at θ = 0.61 λ / a, then the second minimum would be at ~1.22 λ / a, so the distance between them is 0.61 λ / a. Wait, but the answer options have (B) 0.610 λ /a, so maybe that's the answer.

But wait, the problem says "the angular distance between the first two minima". Wait, in the far field, the diffraction pattern for a circular aperture has a central maximum, then the first minimum at θ = 1.22 λ / D, then a secondary maximum, then second minimum at θ = 2.44 λ / D. So the angular separation between first and second minima is (2.44 - 1.22) λ / D = 1.22 λ / D. But in this problem, D = 2a (since the radius is a), so 1.22 λ / (2a) = 0.61 λ / a. So the angular distance between first and second minima is 0.61 λ / a. Then answer B.

Wait, but let me check again. Wait, the problem says "when N is infinitely large". So the polygon becomes a circle with radius R = a? Wait, apothem a for a polygon with N sides, as N→infty, R = a / cos(π/N) ≈ a (since cos(π/N) ≈ 1 - (π^2)/(2N^2) ≈ 1). So R approaches a. So the radius of the circular aperture is a. Then the first minimum is at sinθ = 1.22 λ / (2R) = 1.22 λ / (2a), so θ ≈ 0.61 λ /a. Then the second minimum is at sinθ = 2.44 λ / (2a) = 1.22 λ /a. So the angular distance between the first and second minima is (1.22 λ /a - 0.61 λ /a) = 0.61 λ /a. Wait, but that would be the angular distance. Wait, no: the angular separation between the two minima would be θ2 - θ1 = (2.44 λ / (2a)) - (1.22 λ / (2a)) = (1.22 λ / (2a)) = 0.61 λ /a. Hmm, yes. So the angular distance between the first two minima is 0.61 λ /a. Which is option B.

But wait, another way to think about it: in the Fraunhofer diffraction for a circular aperture, the intensity is given by I = I0 [2J1(ka sinθ)/(ka sinθ)]^2, where J1 is the Bessel function of the first kind. The first minimum occurs when J1(x) = 0, which is at x ≈ 3.8317, so ka sinθ = 3.8317. Wait, hold on, maybe this is a different approach.

Wait, actually, the standard formula for the first minimum in circular aperture diffraction is when the argument of the Bessel function is 3.8317, so the first zero of J1(x) is at x ≈ 3.8317. Then, the angle θ satisfies sinθ = (3.8317 λ)/(2π R), but wait, maybe I need to recall the exact relation.

Let me recall: For a circular aperture of radius R, the diffraction pattern in the far field has intensity given by:

I(θ) = I0 [2 J1( (π R sinθ)/λ ) / ( (π R sinθ)/λ ) ]^2

Wait, different conventions. Hmm, perhaps better to use the standard formula.

In the Fraunhofer diffraction for a circular aperture of diameter D, the first minimum occurs at sinθ = 1.22 λ / D. So if the radius is R, then D = 2R, so sinθ = 1.22 λ / (2R). So θ ≈ 1.22 λ / (2R) for small angles.

In this problem, the aperture is a polygon with N sides, apothem a. As N→∞, the polygon becomes a circle with radius R = a (as established earlier). So R = a.

Therefore, θ ≈ 1.22 λ / (2a) = 0.61 λ /a for the first minimum. Wait, but the problem says "the angular distance between the first two minima". So the first minimum is at θ = 0.61 λ /a, the second minimum is at θ = 1.22 λ /a (since the next zero of the Bessel function is at ~7.014, so 7.014 / 2 = 3.507, which would correspond to sinθ = 3.507 λ / (2R), but maybe my previous thought is conflicting here).

Wait, perhaps confusion arises here. Let's get back to the Bessel function.

The intensity distribution for a circular aperture is proportional to [J1(k a sinθ)/ (k a sinθ)]^2, where a is the radius of the aperture. Wait, different sources use different notations.

Let me check: In the standard treatment, for a circular aperture of radius R, the diffraction pattern has intensity:

I(θ) = I0 [ (2 J1( (π R sinθ)/λ )) / ( (π R sinθ)/λ ) ]^2

So the first minimum occurs when J1(x) = 0, where x = (π R sinθ)/λ. The first zero of J1(x) is at x ≈ 3.8317.

So:

(π R sinθ)/λ = 3.8317

sinθ = (3.8317 λ) / (π R)

For small angles, sinθ ≈ θ, so θ ≈ (3.8317 / π) * (λ / R) ≈ (1.220) * (λ / R)

Ah! So θ ≈ 1.220 λ / R

Wait, so here R is the radius of the aperture.

In this problem, the aperture radius R is equal to a (since as N→∞, R = a). Wait, according to our previous analysis: apothem a = R cos(π/N), so R = a / cos(π/N) ≈ a for large N. So R ≈ a.

Therefore, θ ≈ 1.220 λ / a

Wait, but this conflicts with the previous thought.

Wait, this is critical. Let's parse this carefully.

If the formula gives θ ≈ 1.220 λ / R, where R is the radius of the aperture.

In this problem, R (radius) ≈ a (apothem) for large N.

Therefore, θ ≈ 1.220 λ / a

But the question asks for the angular distance between the first two minima.

Wait, in the Bessel function approach, the first minimum is at x = 3.8317, next zero of J1(x) is at x = 7.0156 (second zero), so the second minimum would be at x = 7.0156.

Therefore, the angular separation between the first and second minima would be:

θ2 - θ1 = [ (7.0156 λ) / (π R) ] - [ (3.8317 λ) / (π R) ] = (3.1839 λ) / (π R) ≈ 1.013 λ / R

Wait, but this is messy. Wait, the problem says "the angular distance between the first two minima". Hmm. Wait, in the diffraction pattern of a circular aperture, there's a central maximum, then the first minimum, then a secondary maximum, then the second minimum, etc. So the first minimum is the first one after the central peak, the second minimum is the next one after the secondary peak. So the angular distance between the first and second minima is θ2 - θ1.

Given that θ1 = 1.220 λ / R (from the first zero of J1), θ2 = (7.0156 / 3.8317) θ1 ≈ 1.831 θ1, so the angular distance between them is ~0.831 θ1. Hmm, but this seems complicated.

Wait, but the problem states "when N is infinitely large", so it's a circular aperture. The question is from an exam, so likely the answer is related to the standard 1.22 λ / D. Let's think again.

Wait, in the problem statement: "the angular distance between the first two minima". If the first minimum is at θ = 1.22 λ / D, then the next minimum is at 2.44 λ / D. So the angular distance is 1.22 λ / D.

But here D is the diameter. If the aperture has radius R = a, then D = 2a. So angular distance = 1.22 λ / (2a) = 0.61 λ /a. So answer B.

But according to the Bessel function calculation, θ = 1.22 λ / R (if R is radius). Wait, confusion here between different conventions.

Let me check a reference. For example, in the standard diffraction formula for a circular aperture of radius R, the first minimum occurs at sinθ = 1.22 λ / (2R). Wait, no:

Wait, according to University Physics textbook (Young and Freedman), the first minimum in the diffraction pattern of a circular aperture is at sinθ = 1.22 λ / D, where D is the diameter. So if D = 2R, then sinθ = 1.22 λ / (2R). So θ ≈ 1.22 λ / (2R) = 0.61 λ / R.

So the angular distance from the center to the first minimum is 0.61 λ / R.

The second minimum would be at sinθ = 2.44 λ / D = 1.22 λ / R, so angular distance from center is 1.22 λ / R.

Therefore, the angular distance between the first and second minima is (1.22 λ / R - 0.61 λ / R) = 0.61 λ / R.

Since in this problem, R = a (as N→∞), then angular distance = 0.61 λ / a. So answer B.

But wait, another thought. The problem says "apothems are of the same length a". For a polygon, apothem is the distance from center to a side. When N→infty, the polygon becomes a circle with radius equal to apothem? Wait, no.

Wait, hold on. Maybe my initial assumption that R = a is wrong.

Let's re-examine the relationship between apothem and radius for a regular polygon.

For a regular polygon with N sides:

- Radius R (circumradius, distance from center to vertex)
- Apothem a (distance from center to side)

The relationship is: a = R cos(π/N)

So R = a / cos(π/N)

As N becomes very large, π/N becomes very small, so cos(π/N) ≈ 1 - (π²)/(2N²), so R ≈ a / [1 - (π²)/(2N²)] ≈ a [1 + (π²)/(2N²)] → a as N→∞.

So yes, R approaches a. So the radius of the circular aperture is a.

Therefore, using the formula θ ≈ 0.61 λ / a for the first minimum (angular distance from center). Then the second minimum is at ~1.22 λ / a, so the angular distance between them is 0.61 λ / a.

Wait, but according to the textbook formula, the angular separation between the first and second minima is 1.22 λ / D (where D is diameter). If D = 2a, then 1.22 λ / (2a) = 0.61 λ /a. So answer B.

But wait, the problem says "the angular distance between the first two minima". So if the first minimum is at 0.61 λ /a and the second at 1.22 λ /a, then the distance between them is 0.61 λ /a. So answer B.

But let's check the options. Option B is 0.610 λ /a. Option A is 1.220 λ /a.

Wait, but in some references, the formula is written as the angular width of the central peak being 1.22 λ / D, so the distance between first and second minima would be 1.22 λ / D. But here D = 2a, so 1.22 λ / (2a) = 0.61 λ /a.

Yes, so answer B.

But wait, another angle: The problem says "angular distance between the first two minima". In the diffraction pattern, the minima are symmetrically placed around the center. So the first minimum on one side is at +θ, the first on the other side at -θ. But the problem says "the angular distance between the first two minima"—probably meaning the separation between the first minimum on one side and the first minimum on the other side? Wait, no, the problem says "the first two minima". Hmm.

Wait, in the far field diffraction pattern of a circular aperture, there is a central maximum, then the first minimum (at ±θ), then a secondary maximum, then the second minimum (at ±2θ), etc. Wait, no. Actually, the diffraction pattern has minima at angles θ_n where n is integer, with the first minimum at θ = 1.22 λ / D, then next at ~2.44 λ / D, etc. So the angular separation between first and second minima (on the same side?) is (2.44 - 1.22) λ / D = 1.22 λ / D.

But the problem says "the angular distance between the first two minima". If it's the distance between the first minimum on one side and the second minimum on the same side, then it's 1.22 λ / D. But if it's the distance between the first minimum and the second minimum on either side (i.e., the width between the first and second minima), then it's 0.61 λ / D.

Wait, the problem states: "the angular distance between the first two minima". Hmm. In typical terminology, for a diffraction pattern with a central peak, the "first minimum" is the first one after the central peak, and the "second minimum" is the next one after the secondary peak. The angular distance between them (on one side) would be θ2 - θ1.

Given that θ1 = 1.22 λ / D, θ2 ≈ 2.44 λ / D, so θ2 - θ1 = 1.22 λ / D.

But here D = 2a, so θ2 - θ1 = 1.22 λ / (2a) = 0.61 λ /a.

Therefore, the answer is B.

Wait, but another way. Let's think about the limit as N approaches infinity. The problem says N is infinitely large. So we can model this as a circular aperture with radius equal to a (since apothem a becomes the radius as N→infty).

The standard formula for the first minimum in the far field is sinθ = 1.22 λ / D, D = 2a. So θ ≈ 1.22 λ / (2a) = 0.61 λ /a. This is the angle from the center to the first minimum. The next minimum is at sinθ = 2.44 λ / (2a) = 1.22 λ /a. So the angular separation between first and second minima is (1.22 - 0.61) λ /a = 0.61 λ /a. So answer B.

Yes, this seems consistent.

Wait, but I've seen some sources say that the angular distance between the first and second minima is 1.22 λ / D. Wait, no, let's get precise.

Suppose D is the diameter. Then the first minimum is at θ = 1.22 λ / D. The second minimum is at θ = 2.44 λ / D. So the angular distance between them is 1.22 λ / D.

But in this problem, the answer options are in terms of λ /a. If D = 2a, then 1.22 λ / D = 0.61 λ /a. So the angular distance between first and second minima is 0.61 λ /a. So answer B.

Yes, that seems to be the case.

Wait, but why does the problem mention "the first two minima"? If it's the first and second minima on the same side of the central maximum, then the angular distance is 0.61 λ /a. If it's the first minimum on one side and the second on the other side, that would be different, but the problem says "the first two minima", which probably refers to the two minima closest to the center (i.e., first and second), so the separation between them.

Given the options, B is 0.610 λ /a, which matches our calculation.

Wait, but option A is 1.220 λ /a. If someone forgot to divide by 2 (i.e., confused radius and diameter), they might pick A. But according to our analysis, it's B.

Wait, another check. Let's recall that in the case of a circular aperture, the first minimum occurs at an angle θ where θ = 1.22 λ / D, D being diameter. So if D = 2a, then θ = 1.22 λ / (2a) = 0.61 λ /a. This is the angle to the first minimum. The next minimum is at θ = 2.44 λ / D = 1.22 λ /a. So the distance between first and second minima is 0.61 λ /a. So answer B.

Yes, I think that's it.

**Final Answer**
\boxed{B}
<
</think>

To determine the **angular distance between the first two minima** in the far field diffraction pattern of a monochromatic light wave incident on a **polygonal aperture** with **infinitely many sides**, we must first understand the physical setup and the limiting behavior as $ N \to \infty $.

---

### Step 1: Understanding the Aperture Shape

The problem describes an **N-sided polygon** with **all apothems of length $ a $**. The **apothem** is the perpendicular distance from the center of a regular polygon to the midpoint of one of its sides.

For a regular polygon with $ N $ sides, the **apothem** $ a $ and the **radius** $ R $ (distance from center to a vertex) are related by:

$$
a = R \cos\left(\frac{\pi}{N}\right)
$$

As $ N \to \infty $, $ \frac{\pi}{N} \to 0 $, so $ \cos\left(\frac{\pi}{N}\right) \to 1 $, and thus:

$$
R \to a
$$

This means that **as $ N \to \infty $**, the polygon becomes a **circle of radius $ a $**.

---

### Step 2: Diffraction Pattern of a Circular Aperture

When monochromatic light of wavelength $ \lambda $ falls on a circular aperture of **radius $ R = a $**, the far-field diffraction pattern is governed by the **Bessel function of the first kind** $ J_1(x) $, where:

$$
x = \frac{\pi R \sin\theta}{\lambda}
$$

The **first minimum** in the diffraction pattern occurs when $ J_1(x) = 0 $, which happens at:

$$
x = \frac{\pi R \sin\theta}{\lambda} = 3.8317 \quad \Rightarrow \quad \sin\theta = \frac{3.8317 \lambda}{\pi R}
$$

For **small angles**, $ \sin\theta \approx \theta $, so:

$$
\theta \approx \frac{3.8317 \lambda}{\pi R}
$$

Substituting $ R = a $, we get:

$$
\theta_1 \approx \frac{3.8317}{\pi} \cdot \frac{\lambda}{a} \approx 1.220 \cdot \frac{\lambda}{a}
$$

This is the **angle to the first minimum** from the center.

The **second minimum** occurs at the **next zero** of $ J_1(x) $, which is at $ x \approx 7.0156 $. So:

$$
\theta_2 \approx \frac{7.0156}{\pi} \cdot \frac{\lambda}{a} \approx 2.234 \cdot \frac{\lambda}{a}
$$

Therefore, the **angular distance between the first and second minima** is:

$$
\Delta\theta = \theta_2 - \theta_1 \approx (2.234 - 1.220) \cdot \frac{\lambda}{a} = 1.014 \cdot \frac{\lambda}{a}
$$

Wait — this seems inconsistent with the standard formula. Let's reconcile this with the **standard diffraction formula** used in optics.

---

### Step 3: Standard Diffraction Formula for Circular Apertures

In most optics contexts, the **first minimum** in the diffraction pattern of a **circular aperture of diameter $ D $** occurs at:

$$
\sin\theta = \frac{1.22 \lambda}{D}
$$

For **small angles**, $ \sin\theta \approx \theta $, so:

$$
\theta_1 \approx \frac{1.22 \lambda}{D}
$$

The **second minimum** occurs at:

$$
\theta_2 \approx \frac{2.44 \lambda}{D}
$$

So the **angular distance between the first and second minima** is:

$$
\Delta\theta = \theta_2 - \theta_1 = \frac{2.44 \lambda - 1.22 \lambda}{D} = \frac{1.22 \lambda}{D}
$$

Now, in our case, the **diameter** $ D $ of the aperture is $ 2a $ (since the radius is $ a $), so:

$$
\Delta\theta = \frac{1.22 \lambda}{2a} = 0.61 \cdot \frac{\lambda}{a}
$$

---

### Step 4: Final Answer

This matches **Option (B)**: $ 0.610 \lambda / a $

The key insight is that the **angular distance between the first two minima** (on the same side of the central maximum) is **not** the full angular width of the central peak, but the **difference** between the second and first minima, which is $ \frac{1.22 \lambda}{D} $, and with $ D = 2a $, this becomes $ 0.61 \lambda / a $.

---

### Final Answer

Final answer: (B)
```

