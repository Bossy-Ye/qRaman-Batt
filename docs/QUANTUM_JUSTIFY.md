# Why Quantum Here 
**Most updates stay classical** — fast, cheap, and good enough for day-to-day recipe tweaks.

**A. Physics-based updates when archives don’t fit.**  
Raman band **positions/intensities** come from **polarizability derivatives** (how α changes along a vibrational mode). When local chemistry/temperature/solvation differs from the archives, we need those **response properties** under *our* conditions to rebuild the expected-bands table (centers, widths, weights) in a defensible way. **LR–VQE / variational subspace + linear-response** methods provide access to excitations and response functions on NISQ hardware, which is a credible path to predicting band shifts/strengths (with uncertainty) for hard cases. 

**B. Robust tagging in noisy/overlapped windows.**  
For per-window labelling (PEAK / DRIFTED / NOT-PEAK) at **low SNR** or with **overlap**, a **quantum kernel (QSVM)** can offer richer feature maps than a classical RBF baseline. We keep QSVM as a drop-in kernel; if it beats RBF on our stress bench, we use it—otherwise we fall back to RBF with the same interface. 
It is plausible that QSVM might help in:
- Small-data regime.
- Subtle shape/OOD differences. 
- Multi-band / multi-condition correlations (future)
---

## Selected references (checked)

**Quantum kernels / QSVM**
- Havlíček *et al.*, “Supervised learning with quantum-enhanced feature spaces,” *Nature* **567.7747**, 209–212 (2019). 
- Schuld, Maria, and Nathan Killoran. “Quantum machine learning in feature Hilbert space,” *Phys. Rev. Lett.* **122.4**, 040504 (2019). 

**VQE excited states / linear response (LR–VQE motivation)**
- McClean *et al.*, “Hybrid quantum-classical hierarchy for mitigation of decoherence and determination of excited states,” *Phys. Rev. A* **95**, 042308 (2017). 
- Higgott, Oscar, Daochen Wang, and Stephen Brierley. “Variational quantum computation of excited states,” *Quantum* **3**, 156 (2019). 
- Colless *et al.*, “Computation of molecular spectra on a quantum processor with an error-resilient algorithm,” *Phys. Rev. X* **8**, 011021 (2018). 
- Huang *et al.*, “Variational quantum computation of molecular linear response properties on a superconducting quantum processor.” *J. Phys. Chem. Lett.* **13.39**, 9114–9121 (2022). 
- Yoshioka, Nobuyuki *et al.*, “Generalized Quantum Subspace Expansion,” *Phys. Rev. Lett.* **129.2**, 020502 (2022). 
- Cai, Xiaoxia *et al.*, “Quantum computation of molecular response properties.” *Phys. Rev. Res.* **2.3**, 033324 (2020). 


**Raman anchors (for bands reference in recipes)**
- EC solvent ring modes: Lee, Ying‐Te “Hydrogen bond effect on the Raman spectrum of liquid ethylene carbonate.” *Journal of Raman spectroscopy* **28.11**, 833-838 (1993). (EC ring near ~717 cm⁻¹ context) 
- In-/operando battery Raman overview: Wang, Yuan *et al.*, “In Situ/Operando Spectroscopic Techniques for Nonaqueous Lithium-Based Batteries,” *The Journal of Physical Chemistry C* **128.49**, 20693-20719 (2024). (broad reference for battery Raman practice) 
- Graphite G/D bands (alignment/health): Ferrari, Andrea Carlo, and John Robertson, “Resonant Raman spectroscopy of disordered, amorphous, and diamondlike carbon,” *Phys. Rev. B* **64.7**, 075414 (2001). 

> These sources back the two claims above: (A) variational subspace/linear-response methods can deliver the **response** data we need to refresh band tables under local conditions; (B) **quantum kernels** are a principled way to try and beat RBF on small, noisy spectral windows.