/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk1_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/* The test suite provides a global EST_CTX *ectx used by other tests. */
extern EST_CTX *ectx;

void rq17_chunk1_missing_test_2(void)
{
    int rc;

    /* Path segments that would result in URIs not beginning with "/.well-known/est" */
    rc = est_client_set_server(ectx, "127.0.0.1", US903_TCP_PORT, ".well-known/foo");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    rc = est_client_set_server(ectx, "127.0.0.1", US903_TCP_PORT, "/well-known/est");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* Case-variant of the reserved segment */
    rc = est_client_set_server(ectx, "127.0.0.1", US903_TCP_PORT, ".WELL-KNOWN");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* Percent-encoded/reserved-character attempt */
    rc = est_client_set_server(ectx, "127.0.0.1", US903_TCP_PORT, "%2E%2E");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* Boundary/extra-segment normalization attempts */
    rc = est_client_set_server(ectx, "127.0.0.1", US903_TCP_PORT, "//simpleenroll");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);
}
