/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk1_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/*
 * Many existing tests reuse a shared EST client context named `ectx`.
 * Declare it here as extern so this test can integrate with the common
 * test harness/setup used by the exemplars.
 */
extern EST_CTX *ectx;

void rq17_chunk1_missing_test_1(void)
{
    int rc = 0;

    /* Case-variant of ".well-known" should be rejected by client-side validation */
    rc = est_client_set_server(ectx, US3496_SERVER_IP, US3496_SERVER_PORT, ".WELL-KNOWN");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* Missing leading dot (i.e., "/well-known/est") represented via path-segment should be rejected */
    rc = est_client_set_server(ectx, US3496_SERVER_IP, US3496_SERVER_PORT, "well-known/est");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* Re-check existing invalid-operation example (operation name as path-segment) */
    rc = est_client_set_server(ectx, US3496_SERVER_IP, US3496_SERVER_PORT, "cacerts");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);
}
