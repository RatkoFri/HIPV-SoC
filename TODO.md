# TODO

- [ ] Book: add a subsection "Resolving control dependencies" (branch/jump flush via `PCSrcE`; Valid can be cancelled by a flush, Ready must stay high so the stage drains).
- [ ] Book, final chapter of "RISC-V SoC": add a summary of how Valid/Ready signals propagate through the pipeline (Ready chain F<-D<-E<-M<-W as OR of "empty" and "next ready"; stall as an AND of downstream valids; bubbles compact; flush clears Valid but never lowers Ready; M is multi-cycle so ReadyM uses DoneM).
