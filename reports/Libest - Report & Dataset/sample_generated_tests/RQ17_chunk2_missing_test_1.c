/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk2_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <stdlib.h>

void rq17_chunk2_missing_test_1(void)
{
    EST_OPERATION operation;
    char *path_seg = NULL;
    EST_ERROR rv;

    /* /fullcmc is an optional operation per the requirement; parser should not claim a known operation */
    rv = est_parse_uri("/fullcmc", &operation, &path_seg);
    CU_ASSERT(operation == EST_OP_MAX);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (path_seg) {
        free(path_seg);
        path_seg = NULL;
    }

    /* /serverkeygen is an optional operation per the requirement; parser should not claim a known operation */
    rv = est_parse_uri("/serverkeygen", &operation, &path_seg);
    CU_ASSERT(operation == EST_OP_MAX);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (path_seg) {
        free(path_seg);
        path_seg = NULL;
    }
}
