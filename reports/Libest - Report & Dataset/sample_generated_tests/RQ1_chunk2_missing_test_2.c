/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk2_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_server.h"

void rq1_chunk2_missing_test_2(void)
{
    int rc;

    /*
     * Verify that attempting to register a CA reenroll callback with a
     * NULL server context does not report success. This exercises server-side
     * callback registration error handling (a minimal server<>CA comms check).
     */
    rc = est_set_ca_reenroll_cb(NULL, NULL);
    CU_ASSERT(rc != EST_ERR_NONE);
}
