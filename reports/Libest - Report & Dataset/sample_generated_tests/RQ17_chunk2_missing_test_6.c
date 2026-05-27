/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk2_missing_test_6.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/*
 * Shared prelude: include CUnit and EST public header so tests can call
 * est_parse_uri, and use EST_ERROR / EST_OPERATION / EST_OP_MAX.
 */

void rq17_chunk2_missing_test_6(void)
{
    EST_ERROR rv;
    EST_OPERATION operation;
    char *path_seg = NULL;

    /* Verify that unsupported/optional operation /fullcmc is not recognized */
    rv = est_parse_uri("/.well-known/est/fullcmc", &operation, &path_seg);
    CU_ASSERT(rv != EST_ERR_NONE);
    CU_ASSERT(operation == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);

    /* Verify that unsupported/optional operation /serverkeygen is not recognized */
    rv = est_parse_uri("/.well-known/est/serverkeygen", &operation, &path_seg);
    CU_ASSERT(rv != EST_ERR_NONE);
    CU_ASSERT(operation == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);
}
