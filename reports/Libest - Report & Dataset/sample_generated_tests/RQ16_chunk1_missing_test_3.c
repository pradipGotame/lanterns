/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ16_chunk1_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

void rq16_chunk1_missing_test_3(void)
{
    /*
     * Test EST client receiving a token auth challenge.
     *
     * The helper will perform an enroll where the server issues an
     * AUTH_TOKEN challenge. The registered callback should supply the token
     * and the operation should succeed.
     */
    us1883_simple_enroll("TC1883-4", US1883_SERVER_IP, EST_ERR_NONE, auth_credentials_token_cb);

    /*
     * callback should have been called
     */
    CU_ASSERT(auth_cred_callback_called == 1);
}
