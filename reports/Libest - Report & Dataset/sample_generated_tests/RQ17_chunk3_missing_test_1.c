/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk3_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <string.h>
#include "est.h"

void rq17_chunk3_missing_test_1(void)
{
    EST_OPERATION operation = EST_OP_MAX;
    char *path_seg = NULL;
    EST_ERROR rc;

    /* Case 1: no path-segment configured -> exact operation path */
    rc = est_parse_uri("/.well-known/est/cacerts", &operation, &path_seg);
    CU_ASSERT(rc == EST_ERR_NONE);
    CU_ASSERT(operation == EST_OP_CACERTS);
    CU_ASSERT(path_seg == NULL);

    /* Case 2: configured single path-segment inserted before operation */
    operation = EST_OP_MAX;
    path_seg = NULL;
    rc = est_parse_uri("/.well-known/est/my-path-seg/cacerts", &operation, &path_seg);
    CU_ASSERT(rc == EST_ERR_NONE);
    CU_ASSERT(operation == EST_OP_CACERTS);
    CU_ASSERT(path_seg != NULL);
    CU_ASSERT(strcmp(path_seg, "my-path-seg") == 0);
}
