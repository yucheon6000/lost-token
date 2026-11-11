# gpqa-recr71WEmXEEMzRgq

Run: gpqa-main-baseline-8gpu; arm: baseline.

Expected: A
Model answer: (none)
Scoring outcome: no extracted final answer; answer source: after_thinking_end.

## Question

A particle is placed in a infinite, one-dimensional potential well with boundaries at x=0 and x=a. If the wall is moved slowly from x=a to x=4a, calculate the work done in this process to move the wall in terms of E. ( E=pi^2\hbar^2/(2ma^2))

(A) - (15/16)E
(B) (63/128) E
(C) -(7/16) E
(D) -(63/64) E

## Final response

```text


To determine the **work done in moving the wall** of an infinite one-dimensional potential well from $ x = 0 $ to $ x = a $ to $ x = 4a $, we consider the **adiabatic process** implied by the phrase "moved slowly." In such a process, the quantum state of the particle remains in the **instantaneous eigenstate** of the Hamiltonian as the well expands.

---

### Step 1: Understand the Initial and Final Energy States

The energy levels of a particle in an infinite square well of width $ L $ are:

$$
E_n(L) = \frac{n^2 \pi^2 \hbar^2}{2mL^2}
$$

Initially, the well has width $ L = a $, and the particle is in the **ground state** $ n = 1 $. The energy is:

$$
E_{\text{initial}} = E = \frac{\pi^2 \hbar^2}{2ma^2}
$$

After the wall is moved to $ x = 4a $, the new well has width $ L = 4a $, and the particle remains in the **same ground state** $ n = 1 $ (due to adiabaticity). The final energy is:

$$
E_{\text{final}} = \frac{\pi^2 \hbar^2}{2m(4a)^2} = \frac{E}{16}
$$

So the **change in energy** of the particle is:

$$
\Delta E = E_{\text{final}} - E_{\text{initial}} = \frac{E}{16} - E = -\frac{15}{16}E
$$

---

### Step 2: Interpret the Work Done

In **thermodynamics**, for an **adiabatic process** (no heat exchange), the **work done on the system** is equal to the **change in internal energy**:

$$
W_{\text{on system}} = \Delta E = -\frac{15}{16}E
$$

However, the problem asks for the **work done in this process to move the wall**, which refers to the **work done by the external agent** (i.e., the person moving the wall). In thermodynamics, this is the **negative** of the work done on the system:

$$
W_{\text{agent}} = -W_{\text{on system}} = -(-\frac{15}{16}E) = -\frac{15}{16}E
$$

This makes sense physically: as the well expands, the particle's energy **decreases**, so the **system does work on the surroundings** (the wall), meaning the **agent must do negative work** — the **particle is doing work on the agent**.

---

### Step 3: Confirm with Physical Intuition

- The particle's energy **decreases** as the well size increases (since energy is inversely proportional to $ L^2 $).
- Therefore, the **system loses energy**, so the **agent does negative work**.
- This matches the calculated value of $ -\frac{15}{16}E $.

---

### Final Answer

$$
\boxed{A}
$$
```

## Full generated reasoning and answer

```text
Okay, let's try to figure out this problem step by step. So, we have a particle in an infinite potential well from x=0 to x=a. Then the wall is moved slowly from x=a to x=4a. We need to calculate the work done in this process in terms of E, where E is given as π²ħ²/(2ma²). Hmm, first, I remember that when you move the walls of a potential well slowly, it's a quasi-static process, so the particle stays in a stationary state. But since the well is expanding, the energy levels will change, and we need to consider the work done as the energy changes.

Wait, the work done should be the change in the energy of the particle, right? Because in a quasi-static process, the work done on the system is equal to the change in its energy. But I need to be careful here. Let me think.

First, let's recall the energy levels of a particle in an infinite well. For a well from 0 to L, the energy levels are E_n = (n²π²ħ²)/(2mL²), where n=1,2,3,...

Initially, the well is from 0 to a, so L = a. The ground state energy is E_1 = π²ħ²/(2ma²), which is exactly the E given in the problem. So E = E_1 initially.

Now, we move the wall slowly to x=4a, so the new well is from 0 to 4a. Let's call the new length L = 4a.

But when we move the wall slowly, the particle might not stay in the same state. Wait, in such a process, the system is adiabatically changed, so the particle remains in the same energy state (n) as it was before the expansion, but the energy levels shift because the well size changes. Wait, no—actually, when you expand the well slowly, the particle will transition to the new energy levels, but since it's a slow process, it's adiabatic, so the particle stays in the same quantum state (n) but with the new well size.

Wait, maybe not exactly. Let's think: For an adiabatic process in quantum mechanics, the system remains in the instantaneous eigenstate of the Hamiltonian. So as we expand the well, each time the well size changes, the particle's wavefunction adjusts to the new eigenstates. But since the process is slow, the particle stays in the same n state (if we consider the expansion as a continuous process), but the energy of that state changes.

Wait, but the initial state is the ground state (n=1) of the well of size a. When we expand the well to 4a, the ground state of the new well has a lower energy (since the energy is proportional to 1/L²), but the particle might not stay in the ground state? Wait, no—if the process is slow, the particle will stay in the same n state (adiabatic following), so the initial state is n=1 (ground state) of size a, then as we expand the well, the particle remains in the n=1 state of the expanding well. Wait, but actually, in an adiabatic expansion, the particle's quantum number n doesn't change; it's the same n as before the expansion.

Wait, let's check. Suppose we have a system that is in a state with quantum number n. If we change the system slowly, the state remains in the n-th eigenstate of the new Hamiltonian. So the energy change for the particle is the difference between the new energy of state n and the old energy of state n.

But in this problem, the particle is initially in the ground state (n=1) of the well of size a. Then, as we expand the well to 4a, the particle remains in the n=1 state (since it's adiabatic), so the work done should be the change in energy of the n=1 state.

Wait, but is that correct? Let's think. If you have a particle in a well, and you expand the well slowly, the energy of the particle will decrease because the ground state energy is proportional to 1/L². So the work done on the system would be negative? Wait, work done by the system or on the system? Hmm, the problem says "work done in this process to move the wall". So the work done by the external agent to move the wall. In thermodynamics, work done by the system is negative of work done on the system. But here, we need to be careful.

Let me recall: In quantum mechanics, when you have a slow expansion (adiabatic), the energy of the system changes. The work done on the system is equal to the change in energy (if there's no heat exchange, which is the case for adiabatic process). Wait, but in this problem, is it adiabatic? The problem says "moved slowly", so it's adiabatic.

Wait, the total energy of the system (the particle) changes as the well size changes. So the work done by the external agent (to move the wall) should equal the change in the particle's energy. Wait, maybe not. Let's think about the force.

Alternatively, the work done in moving the wall can be calculated by integrating the force over the distance. The force exerted by the particle on the wall is related to the derivative of the energy with respect to the wall position.

Wait, perhaps a better approach is to consider that in the adiabatic expansion, the particle remains in the same quantum state (n=1) as the well expands. So the initial energy is E_1(a) = π²ħ²/(2ma²) = E (given). The final energy is E_1(4a) = π²ħ²/(2m(4a)²) = π²ħ²/(2m*16a²) = E/16.

So the change in energy is ΔE = E_final - E_initial = E/16 - E = -15E/16.

But the work done on the system (the particle) is equal to this change in energy (since it's adiabatic, no heat exchange). Wait, but the problem says "work done in this process to move the wall". So the work done by the external agent to move the wall would be the negative of the work done by the system? Hmm.

Wait, in thermodynamics, for a system, the first law is dU = δQ - δW, where δW is work done by the system. But in quantum mechanics, it's a bit different. Maybe in this case, the work done on the system (the particle) is equal to the change in its energy. If the particle's energy decreases, then the work done on the system is negative, meaning the system does work on the external agent. But the problem says "work done in this process to move the wall", which is the work done by the external agent (the person moving the wall), so that would be the negative of the change in the particle's energy.

Wait, let's think carefully.

Suppose the external agent moves the wall from a to 4a. The wall is a boundary, so the potential is infinite at x=4a (after moving). The work done by the external agent would be the integral of the force they apply times the displacement. The force they apply is equal to the force exerted by the particle on the wall (by Newton's third law), but with a sign.

In quantum mechanics, the force on the wall can be related to the derivative of the energy with respect to the wall position. For a particle in a box, the energy is E_n = (n²π²ħ²)/(2mL²), so dE/dL = - (n²π²ħ²)/(mL³). The force on the wall (at position L) would be related to this derivative. Wait, maybe the force exerted by the particle on the wall is proportional to -dE/dL.

Wait, in the case of a particle in a box, the potential is infinite at L, so the wavefunction has a hard wall at L. The energy of the system (the particle) is E_n(L). If we consider the work done by the external agent to move the wall from L1 to L2, then the work done should be the integral of the force exerted by the agent times dL. The force exerted by the agent is equal to the negative of the force exerted by the particle on the wall (since the agent is pushing against the particle's force).

Alternatively, in some references, for a system where you expand the box adiabatically, the work done on the system is equal to the change in energy. Wait, if the system's energy decreases, then the work done on the system is negative, meaning the system does work on the surroundings.

But the problem states: "calculate the work done in this process to move the wall". So "work done to move the wall" is the work done by the external agent. So if the particle's energy decreases, the external agent has to do negative work (i.e., the particle does work on the agent). But the answer choices are all negative (except B), so probably the answer is negative.

Wait, let's see. Let's compute the work done as the integral of the force over the displacement.

The energy of the particle in the n-th state is E_n(L) = (n²π²ħ²)/(2mL²). For adiabatic expansion, the particle remains in the n=1 state (assuming it starts in n=1). So the energy as a function of L is E(L) = (π²ħ²)/(2mL²) (since n=1).

The work done by the external agent to move the wall from L=a to L=4a is the integral from L=a to L=4a of F_ext dL.

But what is F_ext? The force exerted by the external agent is equal to the negative of the force exerted by the particle on the wall. In quantum mechanics, the force on the wall can be related to the derivative of the energy with respect to L.

Wait, for a system in a potential well, the force exerted by the particle on the wall is given by the negative gradient of the energy with respect to the wall position. Wait, perhaps.

Alternatively, consider that when you move the wall, the change in energy dE = -F dL, where F is the force exerted by the particle on the wall. So F = -dE/dL.

Wait, if the energy E decreases as L increases, then dE/dL is negative, so F = -dE/dL is positive. So the force exerted by the particle on the wall is positive (in the direction of increasing L), meaning the particle is pushing the wall outward. Therefore, the external agent has to apply a force in the opposite direction (to move the wall outward), so the work done by the agent is integral of F_ext dL = integral of (-F) dL = - integral F dL.

But from dE = -F dL, then F dL = -dE. So the work done by the agent would be integral F_ext dL = integral (-F) dL = integral dE.

Wait, that seems confusing. Let's try to do it step by step.

Let’s denote L as the length of the well (from 0 to L). Initially, L = a; finally, L = 4a.

The energy of the particle in the n=1 state is E(L) = (π²ħ²)/(2mL²).

The work done on the particle (by the external agent) as the wall is moved is equal to the change in the particle's energy, assuming no heat exchange (adiabatic process). Wait, in thermodynamics, for a system, dU = δQ - δW, where δW is work done by the system. But in quantum mechanics, the energy change for an adiabatic process is equal to the work done on the system (if there's no heat transfer).

Wait, maybe here, the work done on the particle is ΔE = E_final - E_initial.

E_initial = E(a) = π²ħ²/(2ma²) = E (given)

E_final = E(4a) = π²ħ²/(2m(4a)^2) = E/(16)

So ΔE = E/16 - E = -15E/16

If the work done on the particle is ΔE, then the work done by the external agent to move the wall would be -ΔE? Wait, no.

Wait, if the particle's energy decreases (ΔE negative), that means the particle has lost energy. So the external agent has to do negative work (i.e., the particle does work on the agent). But the problem says "work done in this process to move the wall", which is the work done by the agent. So if the agent has to do negative work, that would mean the system (particle) does work on the agent.

But the answer choices have negative values, so maybe the answer is -15E/16, which is option A.

Wait, but wait. Wait a second. In some cases, when you expand the well, you have to consider that the particle might transition to higher states. Wait, the problem says "moved slowly", so adiabatic process. But does the particle stay in the same n?

Wait, if you start with the particle in the ground state of the well of size a, and you expand the well slowly, the particle will remain in the ground state of the expanding well. Because in adiabatic processes, the system remains in the instantaneous eigenstate. So as the well expands, the wavefunction evolves to the ground state of the new well.

But here's a catch: When you expand the well, the initial wavefunction (ground state of size a) is not the ground state of the new well (size 4a). However, in an adiabatic expansion, the system remains in the same quantum number n. Wait, is that true?

Wait, let's think. The energy levels of the well are E_n(L) = n²π²ħ²/(2mL²). If we have a particle in the n=1 state of L=a, then when we slowly increase L to 4a, the system will remain in the n=1 state of the new L. Because the expansion is slow enough that there's no transition to higher states. So yes, it's adiabatic, so n remains 1.

Therefore, the energy change is E_final - E_initial = (1²π²ħ²/(2m(4a)^2)) - (1²π²ħ²/(2ma²)) = E/16 - E = -15E/16.

But the work done by the external agent: In thermodynamics, for a system, the work done on the system is equal to the change in internal energy (if adiabatic). So if the system's energy decreases, the work done on the system is negative, meaning the system does work on the surroundings (the agent).

But the problem says "work done in this process to move the wall". So the work done by the agent to move the wall would be the negative of the work done on the system. Wait, no. Let's clarify.

In thermodynamics, work done by the system is W = ∫ P dV. If the system does work on the surroundings, W is positive. Here, the "system" is the particle in the well. If the particle's energy decreases, that means it's losing energy, so the work done by the particle on the surroundings (the agent) would be positive. Therefore, the work done by the agent to move the wall would be negative (since the agent has to overcome the particle's force).

Wait, this is getting a bit confusing. Let's try to use the formula for work done in adiabatic expansion.

In the adiabatic expansion of a quantum system, the work done on the system is equal to the change in energy. So if the system's energy decreases, the work done on the system is negative. But the problem asks for the work done to move the wall, which is the work done by the agent. So if the work done on the system is negative, that means the agent has done negative work (i.e., the system did work on the agent).

But the answer choices are given as (A) -15/16 E, (B) 63/128 E, etc. So option A is -15/16 E.

But wait, hold on. Maybe I made a mistake here. Let's think again. When you expand the well, the particle's energy decreases, so the work done by the external agent is negative. So the answer is A.

But wait, wait a second. Wait, another thought: In some references, when you move the wall of a potential well, the work done is calculated by considering that the particle might transition to higher energy states. Wait, but in this problem, it's moved slowly, so it's adiabatic, so no transitions. But maybe the initial state is the ground state, but as the well expands, the particle's wavefunction has to adjust, and the energy change is not just the ground state.

Wait, no. For adiabatic processes, the system remains in the instantaneous eigenstate. So starting from n=1, it remains n=1. So the energy change is just the change in the ground state energy.

Wait, but let's check with another approach. Suppose we calculate the work done as the integral of the force over the displacement.

The force exerted by the particle on the wall is F = -dE/dL (from quantum mechanics, the force on the wall is related to the derivative of the energy with respect to L).

Wait, E(L) = π²ħ²/(2mL²), so dE/dL = - π²ħ²/(mL³)

So the force exerted by the particle on the wall is F = -dE/dL = π²ħ²/(mL³)

Wait, but direction matters. If L increases (wall moves to the right), the force exerted by the particle on the wall is to the right (positive direction), so the external agent has to apply a force to the left to move the wall. So the work done by the agent would be the integral from L=a to L=4a of (-F) dL.

Wait, work done by agent is ∫ F_agent dL. Since F_agent is opposite to F_particle, F_agent = -F_particle.

So W = ∫_{a}^{4a} F_agent dL = ∫_{a}^{4a} -F_particle dL

But F_particle = dE/dL? Wait, maybe not.

Alternatively, in classical mechanics, the work done by the external force to move a wall is related to the change in energy. Let's think about the energy.

If the particle's energy decreases as the wall moves out, then the external agent is doing negative work. For example, if you have a spring, expanding it requires work, but here the energy of the particle decreases, so it's like the particle is pushing the wall out, so the agent has to do negative work.

Wait, let's compute the work done as the integral.

Assuming that the work done on the system (particle) is ΔE = E_final - E_initial = -15E/16.

In thermodynamics, for an adiabatic process, the work done on the system is equal to the change in internal energy (ΔU = W_on). So W_on = ΔE = -15E/16.

But the problem asks for the work done to move the wall. If W_on is the work done on the system (particle), then the work done by the agent (external) is -W_on = 15E/16. But that contradicts the answer choices which have negative values.

Hmm, now I'm confused.

Wait, maybe the problem is that when you move the wall, the particle's energy doesn't just change by the ground state. Wait, no, because it's a slow process, so it's adiabatic and stays in the same state.

Wait, let's check the energy levels. For a well of length L, E_n = n²π²ħ²/(2mL²). So when L increases from a to 4a, the energy of the n=1 state becomes E/16.

So the change in energy is E/16 - E = -15E/16.

If the system (particle) loses energy, then the work done on the system is negative. But the work done by the external agent is the negative of that? Wait.

In the first law of thermodynamics: ΔU = Q - W, where W is work done by the system. If it's adiabatic (Q=0), then ΔU = -W. So W = -ΔU.

Here, ΔU is the change in internal energy of the system (particle), which is -15E/16. So W (work done by the system) = -ΔU = 15E/16.

But the problem asks for "work done in this process to move the wall". So that would be the work done by the external agent, which is equal to -W (work done by the system). So work done by agent = -W = -15E/16.

Ah, that makes sense. So according to this:

ΔU = Q - W_by_system

Adiabatic: Q=0, so ΔU = -W_by_system => W_by_system = -ΔU

Work done by agent = -W_by_system = ΔU

Wait, no, let's be precise.

Let me define:

- W_by_system: work done by the system (particle) on the surroundings (the wall).

- Work done on the system (particle) is -W_by_system.

The problem asks for "work done in this process to move the wall", which is the work done by the agent (external) to move the wall. So this would be equal to the work done on the system (particle) plus any other work, but in this case, it's adiabatic so only the work done on the system.

Wait, perhaps better to use the following:

In the adiabatic process, the work done on the system (particle) is equal to the change in its energy. So W_on = ΔE.

If ΔE is negative, then W_on is negative, meaning the system does work on the surroundings (the agent).

But the problem says "work done in this process to move the wall". So the work done by the agent is the negative of W_on.

Wait, if the system does work on the agent (W_on is negative), then the agent has to do negative work (i.e., the system does work on the agent). So the work done by the agent is negative.

Wait, this is getting too convoluted. Let's look for another way.

Suppose we model the work done as the integral of the force exerted by the agent.

The force exerted by the agent is equal to the negative of the force exerted by the particle on the wall.

In quantum mechanics, the force on the wall can be found by considering the derivative of the energy with respect to L.

For a particle in the n-th state, E_n(L) = n²π²ħ²/(2mL²)

The force exerted by the particle on the wall is F = dE/dL (but with a sign). Wait, in classical mechanics, for a spring, F = -kx, but here it's different.

Alternatively, in the limit of a particle in a box, the energy is E = p²/(2m) + V, but V is infinite at the walls. Maybe another approach.

Wait, I found a reference in my mind that when you adiabatically expand a box from L to L', the work done is ∫_{L}^{L'} (dE/dL) dL, but I'm not sure.

Wait, let's think of it as the work done by the external force is the integral of F_ext dL. The force F_ext must balance the force from the particle. If the particle's energy decreases as L increases, then the particle is pushing the wall outward, so F_ext is inward (opposite direction), so F_ext is negative if L is increasing.

But maybe it's better to compute the work done as the integral of the energy change.

Wait, here's a different idea. In the adiabatic expansion, the work done on the system is equal to the change in energy. So if the energy of the system decreases, the work done on the system is negative. The problem asks for the work done to move the wall, which is the work done by the agent. So if the work done on the system is negative, the agent has done negative work (i.e., the system did work on the agent).

So the answer would be -15E/16, which is option A.

But wait, I recall that in some similar problems, when you expand the well, the work done is different because you have to consider the particle transitioning to higher states. Wait, but the problem says "moved slowly", so it's adiabatic and no transitions. So it should stay in n=1.

Wait, but let's check the answer choices. Option A is -15/16 E, which is what we calculated. But wait, another thought: Maybe the particle doesn't stay in n=1. Wait, when you expand the well, the initial wavefunction (ground state of the original well) is a superposition of the new states. But since it's a slow expansion, the particle remains in the same n.

Wait, no. In adiabatic processes, the system remains in the instantaneous eigenstate. So if you start with n=1, it remains n=1. So the energy change is just the ground state energy change.

But wait, here's a catch: The energy levels are proportional to 1/L². So when L becomes 4a, the energy becomes E/16. So the change is -15E/16.

But let's think about another example. Suppose the wall is moved from a to 2a. Then the energy change would be E/4 - E = -3E/4. So the work done would be -3E/4. So for doubling the well, work done is -3E/4. Then moving to 4a would be another expansion.

Wait, but in this problem, it's moved directly from a to 4a. So the calculation is as we did.

But why are there other answer choices? Maybe I'm missing something.

Wait, another possibility: When the wall is moved slowly, the particle might transition to a higher state. But in adiabatic expansion, it shouldn't. However, if the expansion is not slow enough, but the problem states "moved slowly", so adiabatic.

Wait, let's consider the following: The initial state is the ground state of the well of size a. As we expand the well, the wavefunction evolves to the ground state of the new well. But the energy of the ground state decreases.

Wait, but maybe the work done is not just the change in the ground state energy. For example, in some cases, when you have a particle in a box and you expand the box, the work done is related to the integral of the force.

Let's try to compute it as an integral.

Assume that the work done by the external agent is W = ∫_{a}^{4a} F_ext dL.

The force F_ext must counteract the force from the particle. In quantum mechanics, the force on the wall can be related to the derivative of the energy with respect to L.

For a particle in the n-th state, E(L) = n²π²ħ²/(2mL²). The force exerted by the particle on the wall is F = -dE/dL. Wait, why?

In classical mechanics, for a system with energy E(L), the force exerted by the system on a wall at position L is F = -dE/dL (if E is the energy of the system). So if E decreases as L increases, then dE/dL is negative, so F is positive (force in the direction of increasing L).

So F = -dE/dL.

Given E(L) = E_0 / L² (where E_0 = π²ħ²/(2ma²) = E), so dE/dL = -2E_0 / L³.

Therefore, F = -dE/dL = 2E_0 / L³.

Wait, so the force exerted by the particle on the wall is 2E_0 / L³.

But the external agent has to apply a force to move the wall, so F_ext = -F (to move the wall outward, the agent pushes against the particle's force).

Wait, no. If the particle is pushing the wall outward (force in +L direction), then the agent must apply a force in -L direction to move the wall outward. So F_ext = -F.

Wait, but work done by the agent is ∫ F_ext dL. Since dL is positive (from a to 4a), and F_ext is negative (opposite to dL), the work done would be negative.

Let's compute:

W = ∫_{a}^{4a} F_ext dL = ∫_{a}^{4a} (-F) dL = - ∫_{a}^{4a} F dL

F = 2E_0 / L³ (from above)

Wait, E_0 = E (given), so:

W = - ∫_{a}^{4a} (2E / L³) dL = -2E ∫_{a}^{4a} L^{-3} dL

Compute the integral:

∫ L^{-3} dL = (-1)/(2L²) + C

So from a to 4a:

[ -1/(2*(4a)^2) - (-1/(2a²)) ] = [ -1/(32a²) + 1/(2a²) ] = ( -1 + 16 ) / 32a² = 15/(32a²)

Therefore,

W = -2E * (15/(32a²)) * a²? Wait, wait, units:

Wait, the integral ∫ L^{-3} dL has units of 1/L², but multiplied by E (which has units of energy) gives energy.

Wait, let's do it carefully.

The integral ∫_{a}^{4a} L^{-3} dL = [ -1/(2L²) ]_{a}^{4a} = -1/(2*(16a²)) + 1/(2a²) = ( -1/32a² + 1/2a² ) = ( -1 + 16 ) / 32a² = 15/(32a²)

So:

W = -2E * (15/(32a²)) * a² ?

Wait, no, the units of E are energy (Joules), and the integral ∫ L^{-3} dL has units of 1/(length²), but when multiplied by E, we get energy.

Wait, actually, in this calculation, E is given as π²ħ²/(2ma²), which has units of energy. So when we write the integral, the 'a' cancels.

Let's compute:

W = -2E * [ ( -1/(2*(4a)^2) + 1/(2a²) ) ]

Wait, no:

Wait, the integral of L^{-3} dL from a to 4a is [ -1/(2L²) ] from a to 4a = (-1/(2*(16a²))) - (-1/(2a²)) = (-1/(32a²) + 1/(2a²)) = ( (-1 + 16)/32a² ) = 15/(32a²)

So:

W = -2E * (15/(32a²)) * a² ?

Wait, no, the 'a' is a length, but in the expression for E, it's divided by a². Wait, maybe better to do it without units.

Let me re-express:

E = π²ħ²/(2ma²), so E has units of energy.

The integral ∫_{a}^{4a} L^{-3} dL = [ -1/(2L²) ]_{a}^{4a} = ( -1/(2*(4a)^2) + 1/(2a²) ) = ( -1/(32a²) + 1/(2a²) ) = ( (-1 + 16)/32a² ) = 15/(32a²)

So W = -2E * (15/(32a²)) * a² ?

Wait, no. The integral ∫ L^{-3} dL has units of 1/length², but multiplied by E (energy) gives energy.

Wait, actually, in the expression for F = 2E / L³, the units check out: E is energy (J), L is length (m), so F has units of J/m³ = N/m² (not quite), wait, maybe I messed up the relation.

Alternatively, maybe this approach is incorrect.

Let's go back. If the work done on the system is ΔE = -15E/16, and the problem asks for work done to move the wall (by the agent), then it's equal to -ΔE = 15E/16, but that's positive, which is not any of the options. The options have negative values.

Wait, no. If the work done on the system is ΔE = -15E/16, then the work done by the system is -ΔE = 15E/16. But the work done by the agent to move the wall would be negative of that, so -15E/16. Which matches option A.

Yes, this makes sense. In thermodynamics, the work done by the system is W = -ΔU (for adiabatic). So ΔU = -15E/16, so W_by_system = 15E/16. Therefore, the work done by the agent is -W_by_system = -15E/16.

Hence, the answer is A.

But wait, I'm still a bit unsure because I remember some similar problems where the work done is different. Let me think of a different angle.

Suppose we have the particle in the ground state of the well. When we expand the well, the wavefunction of the particle must adjust. The energy of the ground state decreases. The work done by the external agent is the negative of the change in energy (if the system does work on the agent).

Wait, another way: The total energy of the system decreases by 15E/16. This means the particle has given up energy to the surroundings (the agent), so the work done by the particle on the agent is 15E/16. Therefore, the work done by the agent is negative: -15E/16.

Yes, that seems right. So the answer is A.

But wait, looking at the answer choices, option A is -15/16 E, which matches. But why are there other options? Let me check if there's a mistake in assuming n=1.

Wait, another thought: When the wall is moved slowly, the particle might not stay in n=1. For example, if you start with n=1 in the well of size a, and expand it to 4a, the wavefunction initially (at L=a) is ψ_1(x) = sqrt(2/a) sin(πx/a). As you expand the well to L=4a, this wavefunction is not the ground state of the new well. However, in an adiabatic process, the system remains in the instantaneous eigenstate. So the particle's quantum number n remains 1 throughout the process.

Yes, because the expansion is slow, so the particle doesn't have time to transition to higher states. So it stays in n=1.

Hence, the energy change is just the change in the n=1 state.

Therefore, the work done by the agent is -15E/16.

But wait, I found a similar problem online: When you expand a box from L to 2L adiabatically, the work done is -3E/4. Which matches our calculation (E/4 - E = -3E/4). So scaling up, expanding from a to 4a would be a factor of 4, so the energy change is E/16 - E = -15E/16. So the work done should be -15E/16.

Yes, this seems correct. So the answer is A.

But wait, the problem states "the wall is moved slowly from x=a to x=4a". So the final well is from 0 to 4a, so length L=4a.

Yes, so the calculation holds.

I think the answer is A.

**Final Answer**
\boxed{A}
</think>

To determine the **work done in moving the wall** of an infinite one-dimensional potential well from $ x = 0 $ to $ x = a $ to $ x = 4a $, we consider the **adiabatic process** implied by the phrase "moved slowly." In such a process, the quantum state of the particle remains in the **instantaneous eigenstate** of the Hamiltonian as the well expands.

---

### Step 1: Understand the Initial and Final Energy States

The energy levels of a particle in an infinite square well of width $ L $ are:

$$
E_n(L) = \frac{n^2 \pi^2 \hbar^2}{2mL^2}
$$

Initially, the well has width $ L = a $, and the particle is in the **ground state** $ n = 1 $. The energy is:

$$
E_{\text{initial}} = E = \frac{\pi^2 \hbar^2}{2ma^2}
$$

After the wall is moved to $ x = 4a $, the new well has width $ L = 4a $, and the particle remains in the **same ground state** $ n = 1 $ (due to adiabaticity). The final energy is:

$$
E_{\text{final}} = \frac{\pi^2 \hbar^2}{2m(4a)^2} = \frac{E}{16}
$$

So the **change in energy** of the particle is:

$$
\Delta E = E_{\text{final}} - E_{\text{initial}} = \frac{E}{16} - E = -\frac{15}{16}E
$$

---

### Step 2: Interpret the Work Done

In **thermodynamics**, for an **adiabatic process** (no heat exchange), the **work done on the system** is equal to the **change in internal energy**:

$$
W_{\text{on system}} = \Delta E = -\frac{15}{16}E
$$

However, the problem asks for the **work done in this process to move the wall**, which refers to the **work done by the external agent** (i.e., the person moving the wall). In thermodynamics, this is the **negative** of the work done on the system:

$$
W_{\text{agent}} = -W_{\text{on system}} = -(-\frac{15}{16}E) = -\frac{15}{16}E
$$

This makes sense physically: as the well expands, the particle's energy **decreases**, so the **system does work on the surroundings** (the wall), meaning the **agent must do negative work** — the **particle is doing work on the agent**.

---

### Step 3: Confirm with Physical Intuition

- The particle's energy **decreases** as the well size increases (since energy is inversely proportional to $ L^2 $).
- Therefore, the **system loses energy**, so the **agent does negative work**.
- This matches the calculated value of $ -\frac{15}{16}E $.

---

### Final Answer

$$
\boxed{A}
$$
```

