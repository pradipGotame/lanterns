/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk2_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <string.h>
#include <stdlib.h>

void rq17_chunk2_missing_test_2(void)
{
    EST_OPERATION operation;
    char *path_seg;
    EST_ERROR rv;

    /* /fullcmc is listed as an optional operation in the requirement but
     * there is no implementation evidence. Verify it is not recognized. */
    path_seg = NULL;
    rv = est_parse_uri("/.well-known/est/fullcmc", &operation, &path_seg);
    CU_ASSERT(operation == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);
    CU_ASSERT(rv != EST_ERR_NONE);

    /* /serverkeygen is also optional and has no test/implementation evidence.
     * Verify it is not recognized by the URI parser. */
    path_seg = NULL;
    rv = est_parse_uri("/.well-known/est/serverkeygen", &operation, &path_seg);
    CU_ASSERT(operation == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);
    CU_ASSERT(rv != EST_ERR_NONE);
}
