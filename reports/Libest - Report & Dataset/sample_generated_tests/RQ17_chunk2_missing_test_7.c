/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk2_missing_test_7.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

void rq17_chunk2_missing_test_7(void)
{
    EST_ERROR rv;
    EST_OPERATION op;
    char *path_seg = NULL;

    /* Verify that the optional Full CMC operation is not recognized by the parser */
    rv = est_parse_uri("/.well-known/est/fullcmc", &op, &path_seg);
    CU_ASSERT(op == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);

    /* Verify that the optional Server-Side Key Generation operation is not recognized */
    op = EST_OP_MAX;
    path_seg = NULL;
    rv = est_parse_uri("/.well-known/est/serverkeygen", &op, &path_seg);
    CU_ASSERT(op == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);
}
