/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk1_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_client.h"

/*
 * Shared fixtures/contexts (ectx) and server address constants
 * are provided by the existing test harness; this prelude only
 * includes the headers required by the test functions below.
 */

void rq17_chunk1_missing_test_4(void)
{
    int rc = 0;

    /*
     * Attempt to set a server path that does not start with the required
     * "/.well-known/est" prefix (missing the leading dot). The client
     * API is expected to reject invalid path-segments.
     */
    rc = est_client_set_server(ectx, US3496_SERVER_IP, US3496_SERVER_PORT,
                               "/well-known/est");

    /* Expect the client to flag the invalid path segment as in other tests */
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    if (ectx) {
        est_destroy(ectx);
    }
}
