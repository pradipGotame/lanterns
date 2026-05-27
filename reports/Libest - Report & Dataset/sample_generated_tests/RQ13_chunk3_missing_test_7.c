/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_7.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/*
 * Shared prelude for tests in this file: include CUnit and EST public API.
 * The test function(s) assume the common test harness provides a 'server'
 * variable and the usual USxxxx_SERVER_PORT macros as used in exemplars.
 */

void rq13_chunk3_missing_test_7(void)
{
    EST_CTX *ectx = NULL;
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;

    /*
     * Initialize a minimal EST client context. Use NULL/0 for CA chain
     * and a NULL verify callback as in exemplar-style tests.
     */
    ectx = est_client_init(NULL, 0, 0, NULL);
    CU_ASSERT_PTR_NOT_NULL(ectx);

    /*
     * Point the client at an incorrect URI segment and assert the
     * server/handler mapping returns an HTTP Not Found error.
     */
    est_client_set_server(ectx, server, US3512_SERVER_PORT, "/bad_uri");
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_HTTP_NOT_FOUND);

    /*
     * Now point the client at the canonical CSR attributes URI and
     * assert the handler is invoked successfully.
     */
    est_client_set_server(ectx, server, US3512_SERVER_PORT, "/csrattrs");
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Cleanup */
    if (ectx) {
        est_destroy(ectx);
    }
}
