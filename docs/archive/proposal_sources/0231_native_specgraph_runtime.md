# Source: native SpecGraph runtime

The operator described the intended product explicitly:

> Для executor у меня есть ASP - agent surface protocol, но он ещё в разработке. Поэтому меня бы устроил такой вариант, где каким-то образом (скриптом?) создается копия стабильного SpecGraph со всеми инструмениами, разворачивается окружение Python/git/etc и далее агент-разработчик работает с супервизором и тп над конкретным проектом…

The operator subsequently requested: «Да, начинай по канону правок».
The SpecDraft note `specgraph_native_runtime` retains this quote at revision
`1b44588d2b6640de86bd56f219fd4735`; the original message ID and timestamp were
not independently attested. The supervisor intake helper created a pre-canonical
captured intent and an under-review proposal-lane link. This is not approval of
canonical graph publication or a claim of an executor/model run.

Proposal 0227 describes the product workspace boundary; 0230 packages SpecDraft.
This proposal packages a pinned checkout snapshot of the existing engine and
does not introduce ASP or change either proposal's authority. Git, an appropriate
Python interpreter, and the executor remain externally selected prerequisites.
