/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk2_missing_test_5.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

void rq17_chunk2_missing_test_5(void)
{
    EST_ERROR rv;
    EST_OPERATION op;
    char *path_seg = NULL;

    /* /fullcmc is optional and should not be parsed as a known operation */
    rv = est_parse_uri("/.well-known/est/fullcmc", &op, &path_seg);
    CU_ASSERT(op == EST_OP_MAX);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (path_seg) {
        free(path_seg);
        path_seg = NULL;
    }

    /* /serverkeygen is optional and should not be parsed as a known operation */
    rv = est_parse_uri("/.well-known/est/serverkeygen", &op, &path_seg);
    CU_ASSERT(op == EST_OP_MAX);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (path_seg) {
        free(path_seg);
        path_seg = NULL;
    }
}
