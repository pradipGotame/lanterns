/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk2_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <stdlib.h>
#include <string.h>

void rq17_chunk2_missing_test_3(void)
{
    EST_ERROR rv;
    EST_OPERATION op;
    char *path_seg = NULL;

    /* /fullcmc is not one of the four recognized operations and should be reported as EST_OP_MAX */
    rv = est_parse_uri("/.well-known/est/fullcmc", &op, &path_seg);
    CU_ASSERT(op == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);

    /* /serverkeygen is also optional and should likewise be unrecognized by the current parser */
    rv = est_parse_uri("/.well-known/est/serverkeygen", &op, &path_seg);
    CU_ASSERT(op == EST_OP_MAX);
    CU_ASSERT(path_seg == NULL);
}
