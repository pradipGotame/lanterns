/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ16_chunk1_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/* External symbols and helpers provided by the existing test harness/examples */
extern EST_CTX *ectx;
extern int auth_cred_callback_called;
extern int auth_credentials_token_cb();
extern void us1883_simple_enroll();

void rq16_chunk1_missing_test_2(void)
{
    int http_status = 0;

    /* Ensure callback state is clear prior to the test */
    auth_cred_callback_called = 0;

    /*
     * Perform a simple enroll that triggers an auth token challenge.
     * The helper will invoke the registered auth callback so the
     * application can supply credentials (token) and the operation
     * should ultimately succeed.
     */
    us1883_simple_enroll("TC1883-TokenFlow", US1883_SERVER_IP, EST_ERR_NONE, auth_credentials_token_cb);

    /* Verify the auth credential callback was invoked */
    CU_ASSERT(auth_cred_callback_called == 1);

    /* Verify the library exposes the numeric HTTP status and that the
     * final operation completed successfully (HTTP 200).
     */
    http_status = est_client_get_last_http_status(ectx);
    CU_ASSERT(http_status == 200);
}
