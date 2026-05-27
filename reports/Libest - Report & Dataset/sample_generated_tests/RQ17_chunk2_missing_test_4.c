/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk2_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

void rq17_chunk2_missing_test_4(void)
{
    EST_OPERATION op;

    /* The optional operation "fullcmc" should not be recognized by the parser */
    op = est_parse_operation("fullcmc");
    CU_ASSERT(op == EST_OP_MAX);

    /* The optional operation "serverkeygen" should not be recognized by the parser */
    op = est_parse_operation("serverkeygen");
    CU_ASSERT(op == EST_OP_MAX);
}
